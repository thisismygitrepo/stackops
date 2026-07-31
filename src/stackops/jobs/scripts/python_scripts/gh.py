#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "stackops",
# ]
# ///
"""requirements: stackops"""

import json
import shlex
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Final, Literal, NoReturn, TypeAlias
from urllib.parse import quote, urlencode

import typer
from rich.console import Console
from rich.table import Table

from stackops.utils.installer_utils.installer_locator_utils import check_tool_exists
from stackops.utils.options_utils.options import choose_from_options
from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview


CodespaceLocation: TypeAlias = Literal["EastUs", "SouthEastAsia", "WestEurope", "WestUs2"]
OutputFormat: TypeAlias = Literal["table", "json", "names"]

REQUIREMENTS: Final[str] = "stackops"
DEFAULT_LIST_LIMIT: Final[int] = 30
DEFAULT_PREVIEW_SIZE_PERCENT: Final[float] = 70.0
DEFAULT_DOWNLOAD_LOCAL: Final[Path] = Path(".")
REMOTE_PREFIX: Final[str] = "remote:"
BYTES_PER_GIB: Final[int] = 1024**3
LIST_JSON_FIELDS: Final[str] = "createdAt,displayName,gitStatus,lastUsedAt,machineName,name,owner,repository,state,vscsTarget"
VIEW_JSON_FIELDS: Final[str] = (
    "billableOwner,createdAt,devcontainerPath,displayName,environmentId,gitStatus,idleTimeoutMinutes,lastUsedAt,"
    "location,machineDisplayName,machineName,name,owner,prebuild,recentFolders,repository,retentionExpiresAt,"
    "retentionPeriodDays,state,vscsTarget"
)
SSH_TRANSPORT_SUBCOMMANDS: Final[frozenset[str]] = frozenset({"cp", "ssh"})
MISSING_SSH_SERVER_ERROR_MARKERS: Final[tuple[str, ...]] = (
    "failed to start ssh server",
    "check if an ssh server is installed in the container",
    "does not have an ssh server",
)
DEVCONTAINER_SSHD_FEATURE_SNIPPET: Final[str] = """
"features": {
  "ghcr.io/devcontainers/features/sshd:1": {
    "version": "latest"
  }
}
""".strip()
REMOTE_EXEC_COMMAND_ENV: Final[str] = "STACKOPS_GH_EXEC_COMMAND"
REMOTE_EXEC_WRAPPER: Final[str] = (
    f"command_text=${REMOTE_EXEC_COMMAND_ENV}\n"
    """
source_path=
case $command_text in
  '$HOME/'*) source_path=$HOME/${command_text#'$HOME/'} ;;
  '~/'*) source_path=$HOME/${command_text#'~/'} ;;
  /*|./*|../*) source_path=$command_text ;;
esac
if [[ -n $source_path && $source_path == *.sh && -f $source_path ]]; then
  source "$source_path"
else
  eval "$command_text"
fi
"""
).strip()

console = Console()
app = typer.Typer(add_completion=False, no_args_is_help=True, help="Convenient GitHub Codespaces CLI over gh.")


@dataclass(frozen=True, slots=True)
class CodespaceFilters:
    repo: str | None
    repo_owner: str | None
    limit: int


@dataclass(frozen=True, slots=True)
class CodespaceSummary:
    name: str
    display_name: str
    repository: str
    state: str
    machine: str
    last_used_at: str
    created_at: str
    owner: str
    raw: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class MachineSummary:
    name: str
    display_name: str
    operating_system: str
    storage_bytes: int | None
    memory_bytes: int | None
    cpus: int | None
    raw: Mapping[str, object]


class GhcError(Exception):
    pass


def abort(message: str, code: int) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=code)


def is_codespace_ssh_transport_command(args: Sequence[str]) -> bool:
    return len(args) >= 2 and args[0] == "codespace" and args[1] in SSH_TRANSPORT_SUBCOMMANDS


def is_missing_codespace_ssh_server_error(output: str) -> bool:
    normalized = output.casefold()
    return any(marker in normalized for marker in MISSING_SSH_SERVER_ERROR_MARKERS)


def codespace_ssh_server_help() -> str:
    return "\n".join(
        [
            "GitHub Codespaces SSH/cp requires sshd inside the target Codespace.",
            "Add this to .devcontainer/devcontainer.json, rebuild the Codespace, then retry:",
            "",
            DEVCONTAINER_SSHD_FEATURE_SNIPPET,
        ]
    )


def codespace_ssh_server_hint() -> str:
    return "\n".join(
        [
            "",
            "Codespaces SSH/cp hint:",
            "If the error above says the SSH server failed to start, the target Codespace is missing sshd.",
            codespace_ssh_server_help(),
        ]
    )


def run_gh_capture(args: Sequence[str]) -> str:
    command = ["gh", *args]
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise GhcError("gh CLI was not found on PATH.") from error
    if result.returncode != 0:
        output = result.stderr.strip() or result.stdout.strip() or f"gh exited with code {result.returncode}"
        if is_missing_codespace_ssh_server_error(output=output):
            raise GhcError(codespace_ssh_server_help())
        raise GhcError(output)
    return result.stdout


def run_gh_stream(args: Sequence[str]) -> None:
    command = ["gh", *args]
    try:
        result = subprocess.run(command, check=False)
    except FileNotFoundError:
        abort("gh CLI was not found on PATH.", 127)
    if result.returncode != 0:
        if is_codespace_ssh_transport_command(args=args):
            typer.echo(codespace_ssh_server_hint(), err=True)
        raise typer.Exit(code=result.returncode)


def run_gh_stream_with_input(args: Sequence[str], input_data: bytes) -> None:
    command = ["gh", *args]
    try:
        result = subprocess.run(command, input=input_data, check=False)
    except FileNotFoundError:
        abort("gh CLI was not found on PATH.", 127)
    if result.returncode != 0:
        if is_codespace_ssh_transport_command(args=args):
            typer.echo(codespace_ssh_server_hint(), err=True)
        raise typer.Exit(code=result.returncode)


def append_codespace_filters(args: list[str], filters: CodespaceFilters, include_limit: bool) -> None:
    if filters.repo is not None:
        args.extend(["--repo", filters.repo])
    if include_limit:
        args.extend(["--limit", str(filters.limit)])


def append_optional_flag(args: list[str], flag: str, value: str | None) -> None:
    if value is not None:
        args.extend([flag, value])


def append_bool_flag(args: list[str], flag: str, enabled: bool) -> None:
    if enabled:
        args.append(flag)


def decode_json_list(stdout: str) -> list[dict[str, object]]:
    parsed: object = json.loads(stdout)
    if not isinstance(parsed, list):
        raise GhcError("gh returned JSON that was not a list.")
    normalized_items: list[dict[str, object]] = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise GhcError(f"gh returned a non-object item at index {index}.")
        normalized_item: dict[str, object] = {}
        for key, value in item.items():
            if not isinstance(key, str):
                raise GhcError(f"gh returned a non-string JSON key at index {index}.")
            normalized_item[key] = value
        normalized_items.append(normalized_item)
    return normalized_items


def decode_json_object(stdout: str) -> dict[str, object]:
    parsed: object = json.loads(stdout)
    if not isinstance(parsed, dict):
        raise GhcError("gh returned JSON that was not an object.")
    normalized: dict[str, object] = {}
    for key, value in parsed.items():
        if not isinstance(key, str):
            raise GhcError("gh returned a non-string JSON object key.")
        normalized[key] = value
    return normalized


def list_from_json_object(item: Mapping[str, object], key: str) -> list[dict[str, object]]:
    value = item.get(key)
    if not isinstance(value, list):
        raise GhcError(f"gh returned JSON without a '{key}' list.")
    normalized_items: list[dict[str, object]] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise GhcError(f"gh returned a non-object '{key}' item at index {index}.")
        normalized_entry: dict[str, object] = {}
        for entry_key, entry_value in entry.items():
            if not isinstance(entry_key, str):
                raise GhcError(f"gh returned a non-string '{key}' item key at index {index}.")
            normalized_entry[entry_key] = entry_value
        normalized_items.append(normalized_entry)
    return normalized_items


def item_int(item: Mapping[str, object], key: str) -> int | None:
    value = item.get(key)
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def value_to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool | int | float):
        return str(value)
    if isinstance(value, Mapping):
        for key in ("nameWithOwner", "fullName", "name", "login"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def item_text(item: Mapping[str, object], key: str) -> str:
    return value_to_text(item.get(key))


def load_codespaces(filters: CodespaceFilters) -> list[CodespaceSummary]:
    args = ["codespace", "list", "--json", LIST_JSON_FIELDS]
    append_codespace_filters(args=args, filters=filters, include_limit=True)
    raw_items = decode_json_list(stdout=run_gh_capture(args=args))
    summaries: list[CodespaceSummary] = []
    for item in raw_items:
        name = item_text(item=item, key="name")
        if not name:
            raise GhcError("gh returned a codespace without a name.")
        summaries.append(
            CodespaceSummary(
                name=name,
                display_name=item_text(item=item, key="displayName"),
                repository=item_text(item=item, key="repository"),
                state=item_text(item=item, key="state"),
                machine=item_text(item=item, key="machineName"),
                last_used_at=item_text(item=item, key="lastUsedAt"),
                created_at=item_text(item=item, key="createdAt"),
                owner=item_text(item=item, key="owner"),
                raw=item,
            )
        )
    if filters.repo_owner is None:
        return summaries
    owner_prefix = f"{filters.repo_owner}/"
    return [summary for summary in summaries if summary.repository == filters.repo_owner or summary.repository.startswith(owner_prefix)]


def parse_repo_identifier(repo: str) -> tuple[str, str]:
    cleaned = repo.removesuffix(".git").strip("/")
    parts = cleaned.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise GhcError("Repository must use owner/name format.")
    return parts[0], parts[1]


def github_api_endpoint(path: str, params: Mapping[str, str]) -> str:
    query = urlencode(params)
    if not query:
        return path
    return f"{path}?{query}"


def machine_summaries_from_response(response: Mapping[str, object]) -> list[MachineSummary]:
    raw_machines = list_from_json_object(item=response, key="machines")
    machines: list[MachineSummary] = []
    for item in raw_machines:
        name = item_text(item=item, key="name")
        if not name:
            raise GhcError("gh returned a machine without a name.")
        machines.append(
            MachineSummary(
                name=name,
                display_name=item_text(item=item, key="display_name"),
                operating_system=item_text(item=item, key="operating_system"),
                storage_bytes=item_int(item=item, key="storage_in_bytes"),
                memory_bytes=item_int(item=item, key="memory_in_bytes"),
                cpus=item_int(item=item, key="cpus"),
                raw=item,
            )
        )
    return machines


def load_repo_machines(repo: str, branch: str | None, location: CodespaceLocation | None) -> list[MachineSummary]:
    owner, repo_name = parse_repo_identifier(repo=repo)
    path = f"/repos/{quote(owner, safe='')}/{quote(repo_name, safe='')}/codespaces/machines"
    params: dict[str, str] = {}
    if branch is not None:
        params["ref"] = branch
    if location is not None:
        params["location"] = location
    response = decode_json_object(stdout=run_gh_capture(args=["api", github_api_endpoint(path=path, params=params)]))
    return machine_summaries_from_response(response=response)


def load_codespace_machines(codespace_name: str) -> list[MachineSummary]:
    path = f"/user/codespaces/{quote(codespace_name, safe='')}/machines"
    response = decode_json_object(stdout=run_gh_capture(args=["api", path]))
    return machine_summaries_from_response(response=response)


def codespace_label(summary: CodespaceSummary) -> str:
    title = summary.display_name or summary.name
    repo = summary.repository or "-"
    state = summary.state or "-"
    return f"{state} | {repo} | {title} | {summary.name}"


def codespace_preview(summary: CodespaceSummary) -> str:
    raw_json = json.dumps(summary.raw, indent=2, sort_keys=True, ensure_ascii=False, default=str)
    lines = [
        f"# {summary.display_name or summary.name}",
        "",
        f"- Name: `{summary.name}`",
        f"- Repository: `{summary.repository or '-'}`",
        f"- State: `{summary.state or '-'}`",
        f"- Machine: `{summary.machine or '-'}`",
        f"- Owner: `{summary.owner or '-'}`",
        f"- Last used: `{summary.last_used_at or '-'}`",
        f"- Created: `{summary.created_at or '-'}`",
        "",
        "## Raw JSON",
        "",
        "```json",
        raw_json,
        "```",
    ]
    return "\n".join(lines)


def gib_label(value_bytes: int | None) -> str:
    if value_bytes is None:
        return "-"
    return f"{value_bytes / BYTES_PER_GIB:.1f} GiB"


def cpu_label(cpus: int | None) -> str:
    if cpus is None:
        return "-"
    return f"{cpus} CPU"


def machine_label(summary: MachineSummary) -> str:
    display = summary.display_name or summary.name
    return f"{cpu_label(cpus=summary.cpus)} | {gib_label(value_bytes=summary.memory_bytes)} RAM | {gib_label(value_bytes=summary.storage_bytes)} disk | {display} | {summary.name}"


def machine_preview(summary: MachineSummary) -> str:
    raw_json = json.dumps(summary.raw, indent=2, sort_keys=True, ensure_ascii=False, default=str)
    lines = [
        f"# {summary.display_name or summary.name}",
        "",
        f"- Machine ID: `{summary.name}`",
        f"- CPU: `{cpu_label(cpus=summary.cpus)}`",
        f"- RAM: `{gib_label(value_bytes=summary.memory_bytes)}`",
        f"- Storage: `{gib_label(value_bytes=summary.storage_bytes)}`",
        f"- OS: `{summary.operating_system or '-'}`",
        "",
        "## Raw JSON",
        "",
        "```json",
        raw_json,
        "```",
    ]
    return "\n".join(lines)


def select_machine(machines: Sequence[MachineSummary], msg: str) -> MachineSummary | None:
    if not machines:
        return None
    label_to_machine = {machine_label(summary=summary): summary for summary in machines}
    preview_mapping = {label: machine_preview(summary=summary) for label, summary in label_to_machine.items()}
    selected_label = choose_labels(mapping=preview_mapping, msg=msg, multi=False)
    if not isinstance(selected_label, str):
        return None
    return label_to_machine[selected_label]


def resolve_repo_machine_name(repo: str, branch: str | None, location: CodespaceLocation | None) -> str:
    machines = load_repo_machines(repo=repo, branch=branch, location=location)
    selected = select_machine(machines=machines, msg="Select machine type")
    if selected is None:
        abort("No machine selected.", 1)
    return selected.name


def resolve_codespace_machine_name(codespace_name: str) -> str:
    machines = load_codespace_machines(codespace_name=codespace_name)
    selected = select_machine(machines=machines, msg="Select machine type")
    if selected is None:
        abort("No machine selected.", 1)
    return selected.name


def choose_labels(mapping: dict[str, str], msg: str, multi: bool) -> str | list[str] | None:
    if not mapping:
        return [] if multi else None
    if check_tool_exists("tv"):
        if multi:
            return choose_from_dict_with_preview(
                options_to_preview_mapping=mapping, extension="md", multi=True, preview_size_percent=DEFAULT_PREVIEW_SIZE_PERCENT
            )
        return choose_from_dict_with_preview(
            options_to_preview_mapping=mapping, extension="md", multi=False, preview_size_percent=DEFAULT_PREVIEW_SIZE_PERCENT
        )
    if multi:
        return choose_from_options(options=list(mapping.keys()), msg=msg, multi=True, custom_input=False, tv=False)
    return choose_from_options(options=list(mapping.keys()), msg=msg, multi=False, custom_input=False, tv=False)


def select_codespace(summaries: Sequence[CodespaceSummary], msg: str) -> CodespaceSummary | None:
    if not summaries:
        return None
    if len(summaries) == 1:
        return summaries[0]
    label_to_summary = {codespace_label(summary=summary): summary for summary in summaries}
    preview_mapping = {label: codespace_preview(summary=summary) for label, summary in label_to_summary.items()}
    selected_label = choose_labels(mapping=preview_mapping, msg=msg, multi=False)
    if not isinstance(selected_label, str):
        return None
    return label_to_summary[selected_label]


def select_codespaces(filters: CodespaceFilters, msg: str, select_all: bool) -> list[CodespaceSummary]:
    summaries = load_codespaces(filters=filters)
    if not summaries:
        return []
    if select_all:
        return summaries
    label_to_summary = {codespace_label(summary=summary): summary for summary in summaries}
    preview_mapping = {label: codespace_preview(summary=summary) for label, summary in label_to_summary.items()}
    selected_labels = choose_labels(mapping=preview_mapping, msg=msg, multi=True)
    if not isinstance(selected_labels, list):
        return []
    return [label_to_summary[label] for label in selected_labels]


def resolve_explicit_codespace_name(codespace: str, filters: CodespaceFilters) -> str:
    """Resolve a Codespace's API name or unique display name."""
    summaries = load_codespaces(filters=filters)
    for summary in summaries:
        if summary.name == codespace:
            return summary.name
    display_matches = [summary for summary in summaries if summary.display_name == codespace]
    if len(display_matches) == 1:
        return display_matches[0].name
    if len(display_matches) > 1:
        matching_names = ", ".join(summary.name for summary in display_matches)
        raise GhcError(
            f"Display name '{codespace}' is ambiguous. Use one of these Codespace names: {matching_names}"
        )
    # Preserve gh's native behavior and error message for an unknown API name.
    return codespace


def resolve_codespace_name(codespace: str | None, filters: CodespaceFilters, msg: str) -> str:
    if codespace is not None:
        stripped = codespace.strip()
        if stripped:
            return resolve_explicit_codespace_name(codespace=stripped, filters=filters)
    summaries = load_codespaces(filters=filters)
    selected = select_codespace(summaries=summaries, msg=msg)
    if selected is None:
        abort("No codespace selected.", 1)
    return selected.name


def resolve_codespace_names(codespace: str | None, filters: CodespaceFilters, msg: str, select_all: bool) -> list[str]:
    if codespace is not None:
        stripped = codespace.strip()
        if stripped:
            return [resolve_explicit_codespace_name(codespace=stripped, filters=filters)]
    selected = select_codespaces(filters=filters, msg=msg, select_all=select_all)
    if not selected:
        abort("No codespaces selected.", 1)
    return [summary.name for summary in selected]


def newest_codespace_name(filters: CodespaceFilters) -> str:
    summaries = load_codespaces(filters=filters)
    if not summaries:
        abort("No codespaces found after create.", 1)
    newest = max(summaries, key=lambda summary: summary.created_at or summary.last_used_at or summary.name)
    return newest.name


def remote_spec(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        abort("Remote path must not be empty.", 1)
    if stripped.startswith(REMOTE_PREFIX):
        return stripped
    return f"{REMOTE_PREFIX}{stripped}"


def resolved_existing_paths(paths: Sequence[Path]) -> list[Path]:
    resolved: list[Path] = []
    for path in paths:
        expanded = path.expanduser()
        if not expanded.exists():
            abort(f"Local path does not exist: {expanded}", 1)
        resolved.append(expanded.resolve())
    return resolved


def normalize_explicit_upload_remote(remote: str) -> str:
    stripped = remote.strip()
    if not stripped or stripped.startswith(REMOTE_PREFIX):
        return stripped
    local_home = Path.home().resolve()
    candidate = Path(stripped)
    if not candidate.is_absolute():
        return stripped
    try:
        relative = candidate.relative_to(local_home)
    except ValueError:
        return stripped
    normalized = f"~/{relative.as_posix()}"
    if stripped.endswith("/") and not normalized.endswith("/"):
        normalized += "/"
    return normalized


def inferred_upload_remote(sources: Sequence[Path]) -> str:
    home = Path.home().resolve()
    relative_parents: set[Path] = set()
    for source in sources:
        try:
            relative_parents.add(source.parent.relative_to(home))
        except ValueError:
            abort(f"Source is outside the local home directory; provide --remote explicitly: {source}", 1)
    if len(relative_parents) != 1:
        abort("Sources from different directories require an explicit --remote destination.", 1)
    relative_parent = next(iter(relative_parents))
    if relative_parent == Path("."):
        return "~/"
    return f"~/{relative_parent.as_posix()}/"


def upload_remote_directory(remote: str, source_count: int) -> str:
    path = remote.removeprefix(REMOTE_PREFIX).strip()
    if path.endswith("/") or source_count > 1:
        return path.rstrip("/") or "/"
    return str(PurePosixPath(path).parent)


def create_remote_upload_directory(codespace_name: str, remote_directory: str) -> None:
    if remote_directory in {"", ".", "~", "~/"}:
        return
    if remote_directory.startswith("~/"):
        shell_path = f"~/{shlex.quote(remote_directory.removeprefix('~/'))}"
    else:
        shell_path = shlex.quote(remote_directory)
    command = f"mkdir -p -- {shell_path}"
    run_gh_stream(args=["codespace", "ssh", "--codespace", codespace_name, command])


def render_codespaces_table(summaries: Sequence[CodespaceSummary]) -> None:
    table = Table(title="Codespaces")
    table.add_column("State")
    table.add_column("Repository")
    table.add_column("Display")
    table.add_column("Name")
    table.add_column("Machine")
    table.add_column("Last Used")
    for summary in summaries:
        table.add_row(
            summary.state or "-",
            summary.repository or "-",
            summary.display_name or "-",
            summary.name,
            summary.machine or "-",
            summary.last_used_at or "-",
        )
    console.print(table)


def render_machines_table(summaries: Sequence[MachineSummary]) -> None:
    table = Table(title="Codespace Machines")
    table.add_column("Name")
    table.add_column("Display")
    table.add_column("CPU")
    table.add_column("RAM")
    table.add_column("Storage")
    table.add_column("OS")
    for summary in summaries:
        table.add_row(
            summary.name,
            summary.display_name or "-",
            str(summary.cpus) if summary.cpus is not None else "-",
            gib_label(value_bytes=summary.memory_bytes),
            gib_label(value_bytes=summary.storage_bytes),
            summary.operating_system or "-",
        )
    console.print(table)


@app.command("list", help="List codespaces with table, JSON, or names output.", short_help="<l> List codespaces")
def list_cmd(
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces to list.")] = DEFAULT_LIST_LIMIT,
    output_format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format.", case_sensitive=False)] = "table",
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        summaries = load_codespaces(filters=filters)
    except GhcError as error:
        abort(str(error), 1)
    match output_format:
        case "json":
            typer.echo(json.dumps([summary.raw for summary in summaries], indent=2, sort_keys=True, ensure_ascii=False, default=str))
        case "names":
            typer.echo("\n".join(summary.name for summary in summaries))
        case "table":
            render_codespaces_table(summaries=summaries)


@app.command(
    "machines",
    help="List available machine types with CPU, RAM, and storage specs for a repo or selected codespace.",
    short_help="<m> List machine specs",
)
def machines_cmd(
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Repository, owner/name. Uses the repository machine endpoint.")] = None,
    codespace: Annotated[
        str | None, typer.Option("--codespace", "-c", help="Codespace name. Uses the codespace transition machine endpoint.")
    ] = None,
    branch: Annotated[str | None, typer.Option("--branch", "-b", help="Branch or commit to check for repo machines.")] = None,
    location: Annotated[CodespaceLocation | None, typer.Option("--location", "-l", help="Location to check for repo machines.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner when choosing an existing codespace.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
    output_format: Annotated[OutputFormat, typer.Option("--format", "-f", help="Output format.", case_sensitive=False)] = "table",
) -> None:
    if repo is not None and codespace is not None:
        abort("Use either --repo or --codespace, not both.", 1)
    if codespace is not None and (branch is not None or location is not None):
        abort("--branch and --location only apply with --repo.", 1)
    try:
        if repo is not None:
            summaries = load_repo_machines(repo=repo, branch=branch, location=location)
        else:
            filters = CodespaceFilters(repo=None, repo_owner=repo_owner, limit=limit)
            codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to inspect machine options")
            summaries = load_codespace_machines(codespace_name=codespace_name)
    except GhcError as error:
        abort(str(error), 1)
    match output_format:
        case "json":
            typer.echo(json.dumps([summary.raw for summary in summaries], indent=2, sort_keys=True, ensure_ascii=False, default=str))
        case "names":
            typer.echo("\n".join(summary.name for summary in summaries))
        case "table":
            render_machines_table(summaries=summaries)


@app.command(
    help="Create a codespace. If --repo is supplied and --machine is omitted, choose a machine with CPU/RAM/storage preview.",
    short_help="<c> Create codespace",
)
def create(
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Repository, owner/name.")] = None,
    machine: Annotated[
        str | None, typer.Option("--machine", "-m", help="Machine type ID. Omit with --repo to choose from available CPU/RAM/storage specs.")
    ] = None,
    branch: Annotated[str | None, typer.Option("--branch", "-b", help="Repository branch.")] = None,
    display_name: Annotated[str | None, typer.Option("--display-name", "-d", help="Codespace display name.")] = None,
    devcontainer_path: Annotated[str | None, typer.Option("--devcontainer-path", help="Path to devcontainer.json.")] = None,
    location: Annotated[CodespaceLocation | None, typer.Option("--location", "-l", help="Codespace location.")] = None,
    idle_timeout: Annotated[str | None, typer.Option("--idle-timeout", help='Allowed inactivity, for example "10m" or "1h".')] = None,
    retention_period: Annotated[str | None, typer.Option("--retention-period", help='Retention after shutdown, for example "72h".')] = None,
    default_permissions: Annotated[bool, typer.Option("--default-permissions", help="Do not prompt for extra permissions.")] = False,
    status: Annotated[bool, typer.Option("--status", "-s", help="Show post-create and dotfiles status.")] = False,
    web: Annotated[bool, typer.Option("--web", "-w", help="Create codespace from browser.")] = False,
    ssh_after: Annotated[bool, typer.Option("--ssh", help="SSH into the newest matching codespace after creation.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Limit used to find newest codespace after --ssh.")] = DEFAULT_LIST_LIMIT,
) -> None:
    if web and (display_name is not None or idle_timeout is not None or retention_period is not None):
        abort("--web cannot be combined with --display-name, --idle-timeout, or --retention-period.", 1)
    resolved_machine = machine
    if resolved_machine is None and repo is not None and not web:
        try:
            resolved_machine = resolve_repo_machine_name(repo=repo, branch=branch, location=location)
        except GhcError as error:
            abort(str(error), 1)
    args = ["codespace", "create"]
    append_optional_flag(args=args, flag="--repo", value=repo)
    append_optional_flag(args=args, flag="--machine", value=resolved_machine)
    append_optional_flag(args=args, flag="--branch", value=branch)
    append_optional_flag(args=args, flag="--display-name", value=display_name)
    append_optional_flag(args=args, flag="--devcontainer-path", value=devcontainer_path)
    append_optional_flag(args=args, flag="--location", value=location)
    append_optional_flag(args=args, flag="--idle-timeout", value=idle_timeout)
    append_optional_flag(args=args, flag="--retention-period", value=retention_period)
    append_bool_flag(args=args, flag="--default-permissions", enabled=default_permissions)
    append_bool_flag(args=args, flag="--status", enabled=status)
    append_bool_flag(args=args, flag="--web", enabled=web)
    run_gh_stream(args=args)
    if ssh_after:
        filters = CodespaceFilters(repo=repo, repo_owner=None, limit=limit)
        try:
            codespace_name = newest_codespace_name(filters=filters)
        except GhcError as error:
            abort(str(error), 1)
        run_gh_stream(args=["codespace", "ssh", "--codespace", codespace_name])


@app.command(
    help="SSH into a selected codespace. Extra args after the command are passed to ssh.",
    short_help="<s> SSH into codespace",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def ssh(
    ctx: typer.Context,
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to SSH into")
    except GhcError as error:
        abort(str(error), 1)
    args = ["codespace", "ssh", "--codespace", codespace_name]
    if ctx.args:
        args.extend(["--", *ctx.args])
    run_gh_stream(args=args)


@app.command(
    "exec",
    help="Run a remote command through an interactive Bash login shell in a selected codespace.",
    short_help="<x> Execute remote command",
)
def exec_cmd(
    command: Annotated[str, typer.Argument(help="Remote command to run through bash -lic.")],
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to execute command in")
    except GhcError as error:
        abort(str(error), 1)
    remote_command = shlex.join(["env", f"{REMOTE_EXEC_COMMAND_ENV}={command}", "bash", "-lic", REMOTE_EXEC_WRAPPER])
    args = ["codespace", "ssh", "--codespace", codespace_name, "--"]
    if sys.stdin.isatty():
        args.append("-t")
    args.append(remote_command)
    run_gh_stream(args=args)


@app.command(
    "run-script",
    help="Pipe a local script into a selected codespace over gh codespace ssh.",
    short_help="<r> Run local script remotely",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_script(
    ctx: typer.Context,
    script: Annotated[Path, typer.Argument(help="Local script file to pipe into the codespace.")],
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    shell: Annotated[str, typer.Option("--shell", "-S", help="Remote shell used as '<shell> -s --'.")] = "bash",
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    script_path = script.expanduser().resolve()
    if not script_path.is_file():
        abort(f"Script file does not exist: {script_path}", 1)
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to run script in")
    except GhcError as error:
        abort(str(error), 1)
    args = ["codespace", "ssh", "--codespace", codespace_name, "--", shell, "-s", "--", *ctx.args]
    run_gh_stream_with_input(args=args, input_data=script_path.read_bytes())


@app.command(help="Stop one or more selected codespaces.", short_help="<t> Stop codespaces")
def stop(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    all_: Annotated[bool, typer.Option("--all", "-a", help="Stop every codespace matching the filters.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        names = resolve_codespace_names(codespace=codespace, filters=filters, msg="Select codespaces to stop", select_all=all_)
    except GhcError as error:
        abort(str(error), 1)
    for name in names:
        run_gh_stream(args=["codespace", "stop", "--codespace", name])


@app.command(help="Delete selected codespaces, all matching codespaces, or codespaces older than N days.", short_help="<d> Delete codespaces")
def delete(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    all_: Annotated[bool, typer.Option("--all", "-a", help="Delete all codespaces matching gh filters.")] = False,
    days: Annotated[int | None, typer.Option("--days", min=1, help="Delete codespaces older than N days.")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation for unsaved changes.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    if all_ and codespace is not None:
        abort("Use either --all or --codespace, not both.", 1)
    if days is not None and codespace is not None:
        abort("Use either --days or --codespace, not both.", 1)
    if all_ or days is not None:
        args = ["codespace", "delete"]
        if repo is not None:
            args.extend(["--repo", repo])
        if repo_owner is not None:
            args.extend(["--repo-owner", repo_owner])
        append_bool_flag(args=args, flag="--all", enabled=all_)
        if days is not None:
            args.extend(["--days", str(days)])
        append_bool_flag(args=args, flag="--force", enabled=force)
        run_gh_stream(args=args)
        return
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        names = resolve_codespace_names(codespace=codespace, filters=filters, msg="Select codespaces to delete", select_all=False)
    except GhcError as error:
        abort(str(error), 1)
    for name in names:
        args = ["codespace", "delete", "--codespace", name]
        append_bool_flag(args=args, flag="--force", enabled=force)
        run_gh_stream(args=args)


@app.command(help="Upload local files or directories to a selected codespace using gh codespace cp.", short_help="<u> Upload to codespace")
def upload(
    sources: Annotated[list[Path], typer.Argument(help="Local files or directories to upload.")],
    remote: Annotated[
        str | None,
        typer.Option(
            "--remote",
            "-d",
            help="Remote destination. Defaults to the source directory relative to the remote home directory.",
        ),
    ] = None,
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="Recursively copy directories.")] = False,
    expand: Annotated[
        bool,
        typer.Option("--expand", "-e", help="Expand remote paths on the remote shell (enabled by default)."),
    ] = True,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    local_sources = resolved_existing_paths(paths=sources)
    if any(source.is_dir() for source in local_sources) and not recursive:
        abort("Uploading directories requires --recursive.", 1)
    inferred_remote = remote is None
    resolved_remote = (
        inferred_upload_remote(sources=local_sources)
        if inferred_remote
        else normalize_explicit_upload_remote(remote=remote)
    )
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to upload to")
    except GhcError as error:
        abort(str(error), 1)
    remote_directory = upload_remote_directory(remote=resolved_remote, source_count=len(local_sources))
    create_remote_upload_directory(codespace_name=codespace_name, remote_directory=remote_directory)
    args = ["codespace", "cp", "--codespace", codespace_name]
    append_bool_flag(args=args, flag="--recursive", enabled=recursive)
    append_bool_flag(args=args, flag="--expand", enabled=expand)
    args.extend(str(source) for source in local_sources)
    args.append(remote_spec(path=resolved_remote))
    run_gh_stream(args=args)


@app.command(help="Download remote files or directories from a selected codespace using gh codespace cp.", short_help="<w> Download from codespace")
def download(
    remote_sources: Annotated[list[str], typer.Argument(help="Remote files or directories to download.")],
    local: Annotated[Path, typer.Option("--local", "-l", help="Local destination.")] = DEFAULT_DOWNLOAD_LOCAL,
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="Recursively copy directories.")] = False,
    expand: Annotated[bool, typer.Option("--expand", "-e", help="Expand remote path on the remote shell.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    local_dest = local.expanduser()
    if not local_dest.parent.exists():
        abort(f"Local destination parent does not exist: {local_dest.parent}", 1)
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to download from")
    except GhcError as error:
        abort(str(error), 1)
    args = ["codespace", "cp", "--codespace", codespace_name]
    append_bool_flag(args=args, flag="--recursive", enabled=recursive)
    append_bool_flag(args=args, flag="--expand", enabled=expand)
    args.extend(remote_spec(path=source) for source in remote_sources)
    args.append(str(local_dest))
    run_gh_stream(args=args)


@app.command(help="View full JSON details for a selected codespace.", short_help="<v> View codespace details")
def view(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to view")
        output = run_gh_capture(args=["codespace", "view", "--codespace", codespace_name, "--json", VIEW_JSON_FIELDS])
    except GhcError as error:
        abort(str(error), 1)
    typer.echo(json.dumps(json.loads(output), indent=2, sort_keys=True, ensure_ascii=False, default=str))


@app.command(help="Open a selected codespace in VS Code desktop or web.", short_help="<o> Open in VS Code")
def code(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    web: Annotated[bool, typer.Option("--web", "-w", help="Open in VS Code web.")] = False,
    insiders: Annotated[bool, typer.Option("--insiders", help="Use VS Code Insiders.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to open in VS Code")
    except GhcError as error:
        abort(str(error), 1)
    args = ["codespace", "code", "--codespace", codespace_name]
    append_bool_flag(args=args, flag="--web", enabled=web)
    append_bool_flag(args=args, flag="--insiders", enabled=insiders)
    run_gh_stream(args=args)


@app.command(help="Open a selected codespace in JupyterLab.", short_help="<j> Open JupyterLab")
def jupyter(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to open in JupyterLab")
    except GhcError as error:
        abort(str(error), 1)
    run_gh_stream(args=["codespace", "jupyter", "--codespace", codespace_name])


@app.command(help="Show or follow logs for a selected codespace.", short_help="<g> Show logs")
def logs(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Follow logs.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to show logs")
    except GhcError as error:
        abort(str(error), 1)
    args = ["codespace", "logs", "--codespace", codespace_name]
    append_bool_flag(args=args, flag="--follow", enabled=follow)
    run_gh_stream(args=args)


@app.command(help="List forwarded ports for a selected codespace.", short_help="<p> List ports")
def ports(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    raw_json: Annotated[bool, typer.Option("--json", help="Print gh JSON output.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to list ports")
    except GhcError as error:
        abort(str(error), 1)
    args = ["codespace", "ports", "--codespace", codespace_name]
    if raw_json:
        args.extend(["--json", "browseUrl,label,sourcePort,visibility"])
    run_gh_stream(args=args)


@app.command(help="Rebuild a selected codespace.", short_help="<b> Rebuild codespace")
def rebuild(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    full: Annotated[bool, typer.Option("--full", help="Perform a full rebuild.")] = False,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to rebuild")
    except GhcError as error:
        abort(str(error), 1)
    args = ["codespace", "rebuild", "--codespace", codespace_name]
    append_bool_flag(args=args, flag="--full", enabled=full)
    run_gh_stream(args=args)


@app.command(
    help="Edit a selected codespace display name or machine type. If no edit option is supplied, choose a machine with specs preview.",
    short_help="<e> Edit codespace",
)
def edit(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    display_name: Annotated[str | None, typer.Option("--display-name", "-d", help="New display name.")] = None,
    machine: Annotated[str | None, typer.Option("--machine", "-m", help="New machine type.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace to edit")
        resolved_machine = machine
        if resolved_machine is None and display_name is None:
            resolved_machine = resolve_codespace_machine_name(codespace_name=codespace_name)
    except GhcError as error:
        abort(str(error), 1)
    args = ["codespace", "edit", "--codespace", codespace_name]
    append_optional_flag(args=args, flag="--display-name", value=display_name)
    append_optional_flag(args=args, flag="--machine", value=resolved_machine)
    run_gh_stream(args=args)


@app.command("config", help="Print or write OpenSSH config for a selected codespace.", short_help="<k> SSH config")
def config_cmd(
    codespace: Annotated[str | None, typer.Option("--codespace", "-c", help="Codespace name.")] = None,
    repo: Annotated[str | None, typer.Option("--repo", "-R", help="Filter by repository, owner/name.")] = None,
    repo_owner: Annotated[str | None, typer.Option("--repo-owner", help="Filter by repository owner.")] = None,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Write OpenSSH config to this file.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-L", min=1, help="Maximum codespaces in picker.")] = DEFAULT_LIST_LIMIT,
) -> None:
    filters = CodespaceFilters(repo=repo, repo_owner=repo_owner, limit=limit)
    try:
        codespace_name = resolve_codespace_name(codespace=codespace, filters=filters, msg="Select codespace for SSH config")
        ssh_config = run_gh_capture(args=["codespace", "ssh", "--codespace", codespace_name, "--config"])
    except GhcError as error:
        abort(str(error), 1)
    if output is None:
        typer.echo(ssh_config, nl=False)
        return
    output_path = output.expanduser()
    if not output_path.parent.exists():
        abort(f"Output parent does not exist: {output_path.parent}", 1)
    output_path.write_text(ssh_config, encoding="utf-8")
    typer.echo(f"Wrote SSH config to {output_path}")


def register_aliases() -> None:
    app.command("l", hidden=True, help="Alias for list.")(list_cmd)
    app.command("m", hidden=True, help="Alias for machines.")(machines_cmd)
    app.command("c", hidden=True, help="Alias for create.")(create)
    app.command("s", hidden=True, help="Alias for ssh.", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})(ssh)
    app.command("x", hidden=True, help="Alias for exec.")(exec_cmd)
    app.command("r", hidden=True, help="Alias for run-script.", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})(
        run_script
    )
    app.command("t", hidden=True, help="Alias for stop.")(stop)
    app.command("d", hidden=True, help="Alias for delete.")(delete)
    app.command("u", hidden=True, help="Alias for upload.")(upload)
    app.command("w", hidden=True, help="Alias for download.")(download)
    app.command("v", hidden=True, help="Alias for view.")(view)
    app.command("o", hidden=True, help="Alias for code.")(code)
    app.command("j", hidden=True, help="Alias for jupyter.")(jupyter)
    app.command("g", hidden=True, help="Alias for logs.")(logs)
    app.command("p", hidden=True, help="Alias for ports.")(ports)
    app.command("b", hidden=True, help="Alias for rebuild.")(rebuild)
    app.command("e", hidden=True, help="Alias for edit.")(edit)
    app.command("k", hidden=True, help="Alias for config.")(config_cmd)


register_aliases()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
