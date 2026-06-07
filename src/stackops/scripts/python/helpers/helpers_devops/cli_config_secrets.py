import re
import shlex
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, NoReturn, TypeAlias

import typer

from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
    SecretCandidate,
    SecretSelectors,
    load_secret_candidates,
    resolve_candidate,
)
from stackops.utils.schemas.secrets.secrets_loader import SecretsSchemaError, load_secrets_file
from stackops.utils.schemas.secrets.secrets_types import Login, SecretsFile

SECRETS_RELATIVE_PATH = Path(".stackops") / "secrets" / "secrets.json"
SECRETS_SCHEMA_FILENAME = secret_actions.SECRETS_SCHEMA_FILENAME
SECRETS_FILE_VERSION = secret_actions.SECRETS_FILE_VERSION
ENV_VAR_NAME_RE = secret_actions.ENV_VAR_NAME_RE
LOGIN_ENTRY_PATH_RE = re.compile(r"^(entries\[\d+\])(?:\.|$)")
SECRETS_HELP = "Manage StackOps secrets files and define env vars."
SECRETS_SEARCH_HELP = "Define env vars from StackOps secrets files."
SECRETS_STATS_HELP = "Show aggregate StackOps secrets inventory stats without printing secret values."
SECRETS_SEARCH_EPILOG = """Examples:
  devops config secrets search aws dev iam-access-key
  devops config secrets s github personal-access-token
  devops config secrets s AWS_ACCESS_KEY_ID
  devops config secrets search --interactive
  devops config secrets s -i aws
  devops config secrets search --verbose aws dev iam-access-key
  devops config secrets search --name aws-dev --tag iam-access-key
  devops config secrets search --name aws-dev --tag session-token
  devops config secrets search --source global bitwarden
  devops config secrets s --source g bitwarden
  devops config secrets search --source both github token
  devops config secrets s --source b github token
  devops config secrets s -i -P github
  devops config secrets search --path ~/private/team-secrets.json aws dev

Terms are case-insensitive substring matches. All terms must match somewhere across login
name/tags/accountName, secret name/tags/scopes, metadata, or env var keys.
Use search --interactive/-i to choose from matching logins with the TV fuzzy picker.
After interactive selection, StackOps prints a jq command for the selected login entry.
Use search --preview-secrets/-P with --interactive/-i to include secret values in the picker preview.
Use search --verbose/-v to print the selected bundle and env var keys without secret values.
Use search --source to choose the local file (local/l), global source-of-truth file (global/g), or both (both/b). Defaults to both.
With both, missing source files are warned and skipped as long as at least one source exists.
Exact selectors are case-sensitive and can be combined with terms for script-stable matching. Selector short aliases:
--secret-name/-N, --login-tag/-l, --secret-tag/-T, --scope/-S.
"""


SecretsSource: TypeAlias = Literal["local", "l", "global", "g", "both", "b"]
WritableSecretsSource: TypeAlias = Literal["local", "l", "global", "g"]
ResolvedSecretsSource: TypeAlias = Literal["local", "global", "both"]


@dataclass(frozen=True)
class SecretsFileSource:
    name: str
    path: Path


@dataclass(frozen=True)
class SecretsFileStats:
    source_name: str
    path: Path
    exists: bool
    version: str = "-"
    logins: int = 0
    secret_bundles: int = 0
    env_vars: int = 0
    unique_env_keys: int = 0
    duplicate_env_key_occurrences: int = 0
    invalid_env_keys: int = 0
    login_tag_counts: Counter[str] | None = None
    secret_tag_counts: Counter[str] | None = None
    scope_counts: Counter[str] | None = None
    login_description_count: int = 0
    login_url_count: int = 0
    login_email_count: int = 0
    login_username_count: int = 0
    login_account_name_count: int = 0
    login_metadata_count: int = 0
    login_metadata_fields: int = 0
    secret_description_count: int = 0
    secret_rotation_count: int = 0
    secret_metadata_count: int = 0
    secret_metadata_fields: int = 0
    secrets_with_tags: int = 0
    secrets_with_scopes: int = 0
    max_keys_per_secret: int = 0


def search(
    terms: Annotated[
        list[str] | None,
        typer.Argument(
            help=(
                "Case-insensitive terms used to select one secret bundle. All terms must match across login name/tags/accountName, "
                "secret name/tags/scopes, metadata, or env var keys."
            )
        ),
    ] = None,
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        SecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to read: local/l, global/g, or both/b. --path overrides the local source.",
        ),
    ] = "both",
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Choose the secret bundle with a TV fuzzy picker. Terms and exact selectors pre-filter the list."),
    ] = False,
    preview_secrets: Annotated[
        bool, typer.Option("--preview-secrets", "-P", help="Include secret values in the interactive TV preview. Only applies with --interactive/-i.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Print the selected secret bundle and env var keys without secret values.")
    ] = False,
    login_name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Exact login name at entries[].name to require. Use with --tag/--key when a login has multiple secrets."),
    ] = None,
    secret_name: Annotated[str | None, typer.Option("--secret-name", "-N", help="Exact entries[].secrets[].name value to require.")] = None,
    tags: Annotated[
        list[str] | None, typer.Option("--tag", "--tags", "-t", help="Exact login or secret tag to require. Repeat for multiple tags.")
    ] = None,
    login_tags: Annotated[
        list[str] | None, typer.Option("--login-tag", "-l", help="Exact login tag at entries[].tags to require. Repeat for multiple tags.")
    ] = None,
    secret_tags: Annotated[
        list[str] | None, typer.Option("--secret-tag", "-T", help="Exact entries[].secrets[].tags value to require. Repeat for multiple tags.")
    ] = None,
    scopes: Annotated[
        list[str] | None, typer.Option("--scope", "-S", help="Exact entries[].secrets[].scopes value to require. Repeat for multiple scopes.")
    ] = None,
    keys: Annotated[
        list[str] | None, typer.Option("--key", "-k", help="Exact env var key in keyValues to require. Repeat for multiple keys.")
    ] = None,
) -> None:
    """🔐 <S> Define env vars from StackOps secrets files."""
    if preview_secrets and not interactive:
        _fail("--preview-secrets only applies with --interactive/-i.")

    secret_sources = _resolve_secret_sources(secrets_path=secrets_path, secrets_source=secrets_source)
    candidates = _load_secret_candidates_from_sources(secret_sources)
    selectors = SecretSelectors(
        login_name=_clean_optional_selector(login_name),
        secret_name=_clean_optional_selector(secret_name),
        tags=_clean_selector_values(tags),
        login_tags=_clean_selector_values(login_tags),
        secret_tags=_clean_selector_values(secret_tags),
        scopes=_clean_selector_values(scopes),
        keys=_clean_selector_values(keys),
    )
    candidate = resolve_candidate(candidates=candidates, terms=terms, selectors=selectors, interactive=interactive, preview_secrets=preview_secrets)
    candidate_source_path = _candidate_source_path(candidate=candidate, secret_sources=secret_sources)
    if interactive:
        _echo_jq_login_entry_hint(candidate=candidate, secrets_path=candidate_source_path)
    secret_actions.validate_env_names(candidate.key_values)
    secret_actions.write_env_handoff(candidate.key_values)
    if verbose:
        _echo_verbose_selection(candidate=candidate, secrets_path=candidate_source_path)

    names = ", ".join(candidate.key_values)
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Prepared {len(candidate.key_values)} env variable(s)"
    if names:
        msg += f": {names}"
    else:
        msg += "."
    typer.echo(msg)


def stats(
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        SecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to read: local/l, global/g, or both/b. --path overrides the local source.",
        ),
    ] = "both",
    details: Annotated[
        bool,
        typer.Option("--details", "-d", help="Show top non-secret labels such as tags and scopes. Secret values are never printed."),
    ] = False,
    show_paths: Annotated[
        bool,
        typer.Option("--show-paths", help="Include secrets file paths in the source table."),
    ] = False,
    top: Annotated[
        int,
        typer.Option("--top", min=1, max=50, help="Number of tag/scope labels to show with --details."),
    ] = 8,
) -> None:
    """📊 <t> Show aggregate StackOps secrets inventory stats without printing secret values."""
    secret_sources = _resolve_secret_sources(secrets_path=secrets_path, secrets_source=secrets_source)
    stats_rows = _load_secret_stats_from_sources(secret_sources=secret_sources, show_paths=show_paths)
    _render_secret_stats(stats_rows=stats_rows, details=details, show_paths=show_paths, top=top)


def add(
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        WritableSecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to update: local/l or global/g. --path overrides the local source.",
        ),
    ] = "local",
    create: Annotated[
        bool,
        typer.Option("--create", help=f"Allow creating a missing secrets JSON file and {SECRETS_SCHEMA_FILENAME}."),
    ] = False,
) -> None:
    """➕ <a> Append a new login entry to a StackOps secrets file."""
    secret_source = _resolve_single_secret_source(secrets_path=secrets_path, secrets_source=secrets_source)
    secret_actions.add_secrets_entry(secrets_path=secret_source.path, create=create)


def edit(
    secrets_path: Annotated[
        Path | None,
        typer.Option(
            "--path", "-p", help="Override the local secrets JSON file path. Defaults to .stackops/secrets/secrets.json in the current directory."
        ),
    ] = None,
    secrets_source: Annotated[
        WritableSecretsSource,
        typer.Option(
            "--source",
            "-s",
            case_sensitive=False,
            help="Secrets file source to edit: local/l or global/g. --path overrides the local source.",
        ),
    ] = "local",
    create: Annotated[
        bool,
        typer.Option("--create", help=f"Allow creating a missing secrets JSON file and {SECRETS_SCHEMA_FILENAME}."),
    ] = False,
    editor: Annotated[str, typer.Option("--editor", "-E", help="Editor to use. Defaults to hx.")] = "hx",
) -> None:
    """📝 <e> Open a StackOps secrets file for editing."""
    secret_source = _resolve_single_secret_source(secrets_path=secrets_path, secrets_source=secrets_source)
    secret_actions.edit_secrets_file(secrets_path=secret_source.path, editor=editor, create=create)


def get_app() -> typer.Typer:
    app = typer.Typer(
        name="secrets",
        help=f"🔐 <S> {SECRETS_HELP}",
        no_args_is_help=True,
        add_help_option=True,
        add_completion=False,
    )
    app.command("search", no_args_is_help=True, help=f"🔎 <s> {SECRETS_SEARCH_HELP}", epilog=SECRETS_SEARCH_EPILOG)(search)
    app.command("s", no_args_is_help=True, help="Alias for search.", epilog=SECRETS_SEARCH_EPILOG, hidden=True)(search)

    app.command("stats", no_args_is_help=False, help=f"📊 <t> {SECRETS_STATS_HELP}")(stats)
    app.command("t", no_args_is_help=False, help="Alias for stats.", hidden=True)(stats)

    app.command("add", no_args_is_help=False, help="➕ <a> Append a new login entry to a StackOps secrets file.")(add)
    app.command("a", no_args_is_help=False, help="Alias for add.", hidden=True)(add)

    app.command("edit", no_args_is_help=False, help="📝 <e> Open a StackOps secrets file for editing.")(edit)
    app.command("e", no_args_is_help=False, help="Alias for edit.", hidden=True)(edit)

    return app


def _resolve_secret_sources(*, secrets_path: Path | None, secrets_source: SecretsSource) -> list[SecretsFileSource]:
    resolved_source = _resolve_secrets_source_alias(secrets_source)
    local_source = SecretsFileSource(name="local", path=_resolve_local_secrets_path(secrets_path))
    if resolved_source == "local":
        return [local_source]

    global_source = SecretsFileSource(name="global", path=_resolve_global_secrets_path())
    if resolved_source == "global":
        if secrets_path is not None:
            _fail("--path overrides only the local secrets source. Use --source local or --source both with --path.")
        return [global_source]
    if resolved_source == "both":
        return [local_source, global_source]

    _fail(f"Unknown secrets source: {secrets_source}")


def _resolve_single_secret_source(*, secrets_path: Path | None, secrets_source: WritableSecretsSource) -> SecretsFileSource:
    secret_sources = _resolve_secret_sources(secrets_path=secrets_path, secrets_source=secrets_source)
    if len(secret_sources) != 1:
        _fail("Choose exactly one secrets source: local/l or global/g.")
    return secret_sources[0]


def _resolve_secrets_source_alias(secrets_source: SecretsSource) -> ResolvedSecretsSource:
    match secrets_source.casefold():
        case "local" | "l":
            return "local"
        case "global" | "g":
            return "global"
        case "both" | "b":
            return "both"
        case _:
            raise NotImplementedError
    _fail(f"Unknown secrets source: {secrets_source}")


def _resolve_local_secrets_path(secrets_path: Path | None) -> Path:
    if secrets_path is None:
        return Path.cwd() / SECRETS_RELATIVE_PATH
    expanded_path = secrets_path.expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return Path.cwd() / expanded_path


def _resolve_global_secrets_path() -> Path:
    from stackops.utils.source_of_truth import SECRETS_DOFILE

    return SECRETS_DOFILE.expanduser()


def _load_secret_candidates_from_sources(secret_sources: list[SecretsFileSource]) -> list[SecretCandidate]:
    include_source_labels = len(secret_sources) > 1
    candidates: list[SecretCandidate] = []
    missing_sources: list[SecretsFileSource] = []
    for secret_source in secret_sources:
        if not secret_source.path.exists():
            if include_source_labels:
                missing_sources.append(secret_source)
                _warn(f"Secrets file not found for {secret_source.name} source: {secret_source.path}")
                continue
            _fail(f"Secrets file not found: {secret_source.path}")
        candidates.extend(load_secret_candidates(secret_source.path, source_name=secret_source.name if include_source_labels else None))
    if not candidates and missing_sources:
        checked_sources = ", ".join(f"{secret_source.name}={secret_source.path}" for secret_source in missing_sources)
        _fail(f"No secrets files found. Checked: {checked_sources}")
    return candidates


def _candidate_source_path(*, candidate: SecretCandidate, secret_sources: list[SecretsFileSource]) -> Path:
    if candidate.source_path is not None:
        return candidate.source_path
    return secret_sources[0].path


def _load_secret_stats_from_sources(*, secret_sources: list[SecretsFileSource], show_paths: bool) -> list[SecretsFileStats]:
    include_source_labels = len(secret_sources) > 1
    stats_rows: list[SecretsFileStats] = []
    missing_sources: list[SecretsFileSource] = []
    for secret_source in secret_sources:
        if not secret_source.path.exists():
            if include_source_labels:
                missing_sources.append(secret_source)
                stats_rows.append(SecretsFileStats(source_name=secret_source.name, path=secret_source.path, exists=False))
                _warn(_missing_source_message(secret_source=secret_source, show_paths=show_paths))
                continue
            _fail(_missing_source_message(secret_source=secret_source, show_paths=show_paths))
        stats_rows.append(_load_secret_stats(secret_source=secret_source, show_paths=show_paths))

    if missing_sources and not any(row.exists for row in stats_rows):
        checked_sources = _format_checked_sources(secret_sources=missing_sources, show_paths=show_paths)
        _fail(f"No secrets files found. Checked: {checked_sources}")
    return stats_rows


def _load_secret_stats(*, secret_source: SecretsFileSource, show_paths: bool) -> SecretsFileStats:
    try:
        secrets_file = load_secrets_file(secret_source.path)
    except SecretsSchemaError as exc:
        error_text = str(exc) if show_paths else str(exc).replace(str(secret_source.path), secret_source.name)
        _fail(error_text)
    return _build_secret_stats(secrets_file=secrets_file, secret_source=secret_source)


def _build_secret_stats(*, secrets_file: SecretsFile, secret_source: SecretsFileSource) -> SecretsFileStats:
    entries: list[Login] = list(secrets_file["entries"])
    login_tag_counts: Counter[str] = Counter()
    secret_tag_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    env_key_counts: Counter[str] = Counter()

    secret_bundles = 0
    env_vars = 0
    invalid_env_keys = 0
    login_description_count = 0
    login_url_count = 0
    login_email_count = 0
    login_username_count = 0
    login_account_name_count = 0
    login_metadata_count = 0
    login_metadata_fields = 0
    secret_description_count = 0
    secret_rotation_count = 0
    secret_metadata_count = 0
    secret_metadata_fields = 0
    secrets_with_tags = 0
    secrets_with_scopes = 0
    max_keys_per_secret = 0

    for login in entries:
        login_tag_counts.update(login.get("tags", ()))
        login_description_count += int("description" in login)
        login_url_count += int("url" in login)
        login_email_count += int("email" in login)
        login_username_count += int("username" in login)
        login_account_name_count += int("accountName" in login)
        login_metadata = login.get("metadata")
        if login_metadata:
            login_metadata_count += 1
            login_metadata_fields += len(login_metadata)

        for secret in login["secrets"]:
            secret_bundles += 1
            secret_tag_counts.update(secret["tags"])
            scope_counts.update(secret["scopes"])
            secrets_with_tags += int(bool(secret["tags"]))
            secrets_with_scopes += int(bool(secret["scopes"]))
            secret_description_count += int("description" in secret)
            secret_rotation_count += int("rotation" in secret)
            secret_metadata = secret.get("metadata")
            if secret_metadata:
                secret_metadata_count += 1
                secret_metadata_fields += len(secret_metadata)

            key_values = secret["keyValues"]
            env_vars += len(key_values)
            max_keys_per_secret = max(max_keys_per_secret, len(key_values))
            env_key_counts.update(key_values.keys())
            invalid_env_keys += sum(1 for key in key_values if ENV_VAR_NAME_RE.fullmatch(key) is None)

    duplicate_env_key_occurrences = sum(count - 1 for count in env_key_counts.values() if count > 1)
    return SecretsFileStats(
        source_name=secret_source.name,
        path=secret_source.path,
        exists=True,
        version=str(secrets_file["version"]),
        logins=len(entries),
        secret_bundles=secret_bundles,
        env_vars=env_vars,
        unique_env_keys=len(env_key_counts),
        duplicate_env_key_occurrences=duplicate_env_key_occurrences,
        invalid_env_keys=invalid_env_keys,
        login_tag_counts=login_tag_counts,
        secret_tag_counts=secret_tag_counts,
        scope_counts=scope_counts,
        login_description_count=login_description_count,
        login_url_count=login_url_count,
        login_email_count=login_email_count,
        login_username_count=login_username_count,
        login_account_name_count=login_account_name_count,
        login_metadata_count=login_metadata_count,
        login_metadata_fields=login_metadata_fields,
        secret_description_count=secret_description_count,
        secret_rotation_count=secret_rotation_count,
        secret_metadata_count=secret_metadata_count,
        secret_metadata_fields=secret_metadata_fields,
        secrets_with_tags=secrets_with_tags,
        secrets_with_scopes=secrets_with_scopes,
        max_keys_per_secret=max_keys_per_secret,
    )


def _render_secret_stats(*, stats_rows: list[SecretsFileStats], details: bool, show_paths: bool, top: int) -> None:
    from rich.console import Console

    console = Console()
    loaded_stats = [stats_row for stats_row in stats_rows if stats_row.exists]
    console.print(_secret_stats_source_table(stats_rows=stats_rows, show_paths=show_paths))
    if not loaded_stats:
        return
    console.print(_secret_stats_totals_table(stats_rows=loaded_stats))
    console.print(_secret_stats_coverage_table(stats_rows=loaded_stats))
    if details:
        details_table = _secret_stats_details_table(stats_rows=loaded_stats, top=top)
        if details_table.row_count:
            console.print(details_table)


def _secret_stats_source_table(*, stats_rows: list[SecretsFileStats], show_paths: bool):
    from rich import box
    from rich.markup import escape
    from rich.table import Table

    table = Table(title="StackOps Secrets Sources", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Source", style="bold")
    table.add_column("Status")
    table.add_column("Version", justify="right")
    table.add_column("Logins", justify="right")
    table.add_column("Bundles", justify="right")
    table.add_column("Env Vars", justify="right")
    table.add_column("Unique Keys", justify="right")
    table.add_column("Invalid Keys", justify="right")
    if show_paths:
        table.add_column("File")

    for stats_row in stats_rows:
        status = "[green]loaded[/green]" if stats_row.exists else "[yellow]missing[/yellow]"
        row = [
            escape(stats_row.source_name),
            status,
            escape(stats_row.version),
            str(stats_row.logins) if stats_row.exists else "-",
            str(stats_row.secret_bundles) if stats_row.exists else "-",
            str(stats_row.env_vars) if stats_row.exists else "-",
            str(stats_row.unique_env_keys) if stats_row.exists else "-",
            str(stats_row.invalid_env_keys) if stats_row.exists else "-",
        ]
        if show_paths:
            row.append(escape(str(stats_row.path)))
        table.add_row(*row)
    return table


def _secret_stats_totals_table(*, stats_rows: list[SecretsFileStats]):
    from rich import box
    from rich.table import Table

    table = Table(title="Inventory Totals", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    table.add_row("Sources loaded", str(len(stats_rows)))
    table.add_row("Logins", str(sum(row.logins for row in stats_rows)))
    table.add_row("Secret bundles", str(sum(row.secret_bundles for row in stats_rows)))
    table.add_row("Env vars", str(sum(row.env_vars for row in stats_rows)))
    table.add_row("Unique env var names", str(_unique_env_key_total(stats_rows)))
    table.add_row("Duplicate env var occurrences", str(sum(row.duplicate_env_key_occurrences for row in stats_rows)))
    table.add_row("Invalid env var names", str(sum(row.invalid_env_keys for row in stats_rows)))
    table.add_row("Login tags", str(sum(_counter_total(row.login_tag_counts) for row in stats_rows)))
    table.add_row("Secret tags", str(sum(_counter_total(row.secret_tag_counts) for row in stats_rows)))
    table.add_row("Scopes", str(sum(_counter_total(row.scope_counts) for row in stats_rows)))
    table.add_row("Rotation records", str(sum(row.secret_rotation_count for row in stats_rows)))
    table.add_row("Metadata fields", str(sum(row.login_metadata_fields + row.secret_metadata_fields for row in stats_rows)))
    table.add_row("Max env vars in one bundle", str(max((row.max_keys_per_secret for row in stats_rows), default=0)))
    return table


def _secret_stats_coverage_table(*, stats_rows: list[SecretsFileStats]):
    from rich import box
    from rich.table import Table

    total_logins = sum(row.logins for row in stats_rows)
    total_secrets = sum(row.secret_bundles for row in stats_rows)
    table = Table(title="Metadata Coverage", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Field")
    table.add_column("With Field", justify="right")
    table.add_column("Coverage", justify="right")
    table.add_row("Login descriptions", str(sum(row.login_description_count for row in stats_rows)), _percent(sum(row.login_description_count for row in stats_rows), total_logins))
    table.add_row("Login URLs", str(sum(row.login_url_count for row in stats_rows)), _percent(sum(row.login_url_count for row in stats_rows), total_logins))
    table.add_row("Login emails", str(sum(row.login_email_count for row in stats_rows)), _percent(sum(row.login_email_count for row in stats_rows), total_logins))
    table.add_row("Login usernames", str(sum(row.login_username_count for row in stats_rows)), _percent(sum(row.login_username_count for row in stats_rows), total_logins))
    table.add_row("Login account names", str(sum(row.login_account_name_count for row in stats_rows)), _percent(sum(row.login_account_name_count for row in stats_rows), total_logins))
    table.add_row("Login metadata", str(sum(row.login_metadata_count for row in stats_rows)), _percent(sum(row.login_metadata_count for row in stats_rows), total_logins))
    table.add_row("Secret descriptions", str(sum(row.secret_description_count for row in stats_rows)), _percent(sum(row.secret_description_count for row in stats_rows), total_secrets))
    table.add_row("Secret rotations", str(sum(row.secret_rotation_count for row in stats_rows)), _percent(sum(row.secret_rotation_count for row in stats_rows), total_secrets))
    table.add_row("Secret metadata", str(sum(row.secret_metadata_count for row in stats_rows)), _percent(sum(row.secret_metadata_count for row in stats_rows), total_secrets))
    table.add_row("Secret tags", str(sum(row.secrets_with_tags for row in stats_rows)), _percent(sum(row.secrets_with_tags for row in stats_rows), total_secrets))
    table.add_row("Secret scopes", str(sum(row.secrets_with_scopes for row in stats_rows)), _percent(sum(row.secrets_with_scopes for row in stats_rows), total_secrets))
    return table


def _secret_stats_details_table(*, stats_rows: list[SecretsFileStats], top: int):
    from rich import box
    from rich.markup import escape
    from rich.table import Table

    rows: list[tuple[str, str, int]] = []
    for label, counter in (
        ("Login tag", _merge_counters(stats_rows, "login_tag_counts")),
        ("Secret tag", _merge_counters(stats_rows, "secret_tag_counts")),
        ("Scope", _merge_counters(stats_rows, "scope_counts")),
    ):
        rows.extend((label, value, count) for value, count in _top_counter_items(counter, top=top))

    table = Table(title="Top Labels", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Type")
    table.add_column("Value")
    table.add_column("Count", justify="right")
    for row_type, value, count in rows:
        table.add_row(row_type, escape(value), str(count))
    return table


def _percent(count: int, total: int) -> str:
    if total == 0:
        return "-"
    return f"{count / total:.0%}"


def _counter_total(counter: Counter[str] | None) -> int:
    return sum((counter or Counter()).values())


def _merge_counters(stats_rows: list[SecretsFileStats], attribute_name: str) -> Counter[str]:
    merged = Counter[str]()
    for stats_row in stats_rows:
        merged.update(getattr(stats_row, attribute_name) or Counter())
    return merged


def _top_counter_items(counter: Counter[str], *, top: int) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:top]


def _unique_env_key_total(stats_rows: list[SecretsFileStats]) -> int:
    if len(stats_rows) == 1:
        return stats_rows[0].unique_env_keys
    return sum(row.unique_env_keys for row in stats_rows)


def _missing_source_message(*, secret_source: SecretsFileSource, show_paths: bool) -> str:
    if show_paths:
        return f"Secrets file not found for {secret_source.name} source: {secret_source.path}"
    return f"Secrets file not found for {secret_source.name} source."


def _format_checked_sources(*, secret_sources: list[SecretsFileSource], show_paths: bool) -> str:
    if show_paths:
        return ", ".join(f"{secret_source.name}={secret_source.path}" for secret_source in secret_sources)
    return ", ".join(secret_source.name for secret_source in secret_sources)


def _echo_jq_login_entry_hint(*, candidate: SecretCandidate, secrets_path: Path) -> None:
    typer.echo("Selected login entry jq:")
    typer.echo(f"  {_jq_login_entry_command(candidate=candidate, secrets_path=secrets_path)}")


def _jq_login_entry_command(*, candidate: SecretCandidate, secrets_path: Path) -> str:
    return f"jq {shlex.quote(_jq_login_entry_filter(candidate))} {shlex.quote(str(secrets_path))}"


def _jq_login_entry_filter(candidate: SecretCandidate) -> str:
    match = LOGIN_ENTRY_PATH_RE.match(candidate.json_path)
    if match is None:
        return ".entries[]"
    return f".{match.group(1)}"


def _clean_optional_selector(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _clean_selector_values(values: list[str] | None) -> tuple[str, ...]:
    return tuple(stripped_value for value in values or () if (stripped_value := value.strip()))


def _echo_verbose_selection(*, candidate: SecretCandidate, secrets_path: Path) -> None:
    typer.echo("Selected secret bundle:")
    typer.echo(f"  Bundle: {_candidate_verbose_label(candidate)}")
    typer.echo(f"  Source: {secrets_path}")
    typer.echo(f"  JSON path: {candidate.json_path}")
    typer.echo(f"  Login tags: {_join_display(candidate.login_tags)}")
    typer.echo(f"  Secret tags: {_join_display(candidate.secret_tags)}")
    typer.echo(f"  Scopes: {_join_display(candidate.scopes)}")
    typer.echo("Defining env vars:")
    for key in candidate.key_values:
        typer.echo(f"  {key}")


def _candidate_verbose_label(candidate: SecretCandidate) -> str:
    return f"{candidate.login_name} / {candidate.secret_name}"


def _join_display(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)


def _warn(message: str) -> None:
    typer.echo(typer.style("Warning: ", fg=typer.colors.YELLOW) + message, err=True)
