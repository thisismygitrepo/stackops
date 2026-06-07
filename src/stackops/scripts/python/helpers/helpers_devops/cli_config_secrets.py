import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, Mapping, NoReturn, TypeAlias

import typer

from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
    SecretCandidate,
    SecretSelectors,
    load_secret_candidates,
    resolve_candidate,
)
from stackops.utils.schemas.secrets.secrets_types import Login

SECRETS_RELATIVE_PATH = Path(".stackops") / "secrets" / "secrets.json"
SECRETS_SCHEMA_FILENAME = secret_actions.SECRETS_SCHEMA_FILENAME
SECRETS_FILE_VERSION = secret_actions.SECRETS_FILE_VERSION
ENV_VAR_NAME_RE = secret_actions.ENV_VAR_NAME_RE
LOGIN_ENTRY_PATH_RE = re.compile(r"^(entries\[\d+\])(?:\.|$)")
SECRETS_HELP = "Define env vars from StackOps secrets files."
SECRETS_EPILOG = """Examples:
  devops config secrets aws dev iam-access-key
  devops config secrets github personal-access-token
  devops config secrets AWS_ACCESS_KEY_ID
  devops config secrets --interactive
  devops config secrets -i aws
  devops config secrets --verbose aws dev iam-access-key
  devops config secrets --name aws-dev --tag iam-access-key
  devops config secrets --name aws-dev --tag session-token
  devops config secrets --source global bitwarden
  devops config secrets --source g bitwarden
  devops config secrets --source both github token
  devops config secrets --source b github token
  devops config secrets -i -P github
  devops config secrets --path ~/private/team-secrets.json aws dev
  devops config secrets --edit
  devops config secrets --edit --create
  devops config secrets --add
  devops config secrets --add --create

Terms are case-insensitive substring matches. All terms must match somewhere across login
name/tags/accountName, secret name/tags/scopes, metadata, or env var keys.
Use --interactive/-i to choose from matching logins with the TV fuzzy picker.
After interactive selection, StackOps prints a jq command for the selected login entry.
Use --preview-secrets/-P with --interactive/-i to include secret values in the picker preview.
Use --verbose/-v to print the selected bundle and env var keys without secret values.
Use --source to choose the local file (local/l), global source-of-truth file (global/g), or both (both/b). Defaults to both.
With both, missing source files are warned and skipped as long as at least one source exists.
Use --add to append a new entry through prompts.
Use --create with --edit or --add to allow creating a missing secrets file and schema.
Exact selectors are case-sensitive and can be combined with terms for script-stable matching. Selector short aliases:
--secret-name/-N, --login-tag/-l, --secret-tag/-T, --scope/-S.
"""


SecretsSource: TypeAlias = Literal["local", "l", "global", "g", "both", "b"]
ResolvedSecretsSource: TypeAlias = Literal["local", "global", "both"]


@dataclass(frozen=True)
class SecretsFileSource:
    name: str
    path: Path


def secrets(
    ctx: typer.Context,
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
    edit: Annotated[bool, typer.Option("--edit", "-e", help="Open the secrets JSON file for editing instead of loading env vars.")] = False,
    add: Annotated[bool, typer.Option("--add", help="Step through prompts to append a new login entry to the secrets JSON file.")] = False,
    create: Annotated[
        bool,
        typer.Option("--create", help="Allow --edit or --add to create a missing secrets JSON file and secrets.schema.json."),
    ] = False,
    editor: Annotated[str, typer.Option("--editor", "-E", help="Editor to use with --edit. Defaults to hx.")] = "hx",
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
    if edit and add:
        _fail("--edit and --add cannot be used together.")
    if create and not (edit or add):
        _fail("--create only applies with --edit or --add.")

    if preview_secrets and not interactive:
        _fail("--preview-secrets only applies with --interactive/-i.")

    if (edit or add) and _resolve_secrets_source_alias(secrets_source) == "both" and not _parameter_was_provided(ctx, "secrets_source"):
        secret_sources = _resolve_secret_sources(secrets_path=secrets_path, secrets_source="local")
    else:
        secret_sources = _resolve_secret_sources(secrets_path=secrets_path, secrets_source=secrets_source)
    if edit:
        if len(secret_sources) != 1:
            _fail("--edit can only open one secrets file. Choose --source local or --source global.")
        _edit_secrets_file(secrets_path=secret_sources[0].path, editor=editor, create=create)
        return

    if add:
        if len(secret_sources) != 1:
            _fail("--add can only update one secrets file. Choose --source local or --source global.")
        _add_secrets_entry(secrets_path=secret_sources[0].path, create=create)
        return

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
    _validate_env_names(candidate.key_values)
    _write_env_handoff(candidate.key_values)
    if verbose:
        _echo_verbose_selection(candidate=candidate, secrets_path=candidate_source_path)

    names = ", ".join(candidate.key_values)
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Prepared {len(candidate.key_values)} env variable(s)"
    if names:
        msg += f": {names}"
    else:
        msg += "."
    typer.echo(msg)


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


def _parameter_was_provided(ctx: typer.Context, param_name: str) -> bool:
    try:
        import click

        return ctx.get_parameter_source(param_name) is click.core.ParameterSource.COMMANDLINE
    except Exception:
        return False


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


def _edit_secrets_file(secrets_path: Path, editor: str, *, create: bool = False) -> None:
    secret_actions._edit_secrets_file(
        secrets_path=secrets_path,
        editor=editor,
        create=create,
        shutil_module=shutil,
        subprocess_module=subprocess,
    )


def _add_secrets_entry(secrets_path: Path, *, create: bool = False) -> None:
    secret_actions._add_secrets_entry(
        secrets_path=secrets_path,
        create=create,
        prompt_secret_login_entry=_prompt_secret_login_entry,
    )


def _prompt_secret_login_entry() -> Login:
    return secret_actions._prompt_secret_login_entry()


def _clean_optional_selector(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _clean_selector_values(values: list[str] | None) -> tuple[str, ...]:
    return tuple(stripped_value for value in values or () if (stripped_value := value.strip()))


def _validate_env_names(key_values: Mapping[str, object]) -> None:
    secret_actions._validate_env_names(key_values)


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


def _write_env_handoff(key_values: Mapping[str, object]) -> None:
    secret_actions._write_env_handoff(key_values)


def _render_env_file(key_values: Mapping[str, object], powershell: bool) -> str:
    return secret_actions._render_env_file(key_values=key_values, powershell=powershell)


def _render_loader_file(env_path: Path, powershell: bool) -> str:
    return secret_actions._render_loader_file(env_path=env_path, powershell=powershell)


def _quote_powershell(value: str) -> str:
    return secret_actions._quote_powershell(value)


def _chmod_private(path: Path, mode: int) -> None:
    secret_actions._chmod_private(path=path, mode=mode)


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)


def _warn(message: str) -> None:
    typer.echo(typer.style("Warning: ", fg=typer.colors.YELLOW) + message, err=True)
