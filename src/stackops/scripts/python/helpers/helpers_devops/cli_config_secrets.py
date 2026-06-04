import os
import platform
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Mapping, NoReturn

import typer

from stackops.secrets import SecretJsonValue, render_secret_value
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
    SecretCandidate,
    SecretSelectors,
    load_secret_candidates,
    resolve_candidate,
)

SECRETS_RELATIVE_PATH = Path(".stackops") / "secrets" / "secrets.json"
ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SECRETS_HELP = "Define env vars from .stackops/secrets/secrets.json."
SECRETS_EPILOG = """Examples:
  devops config secrets aws dev iam-access-key
  devops config secrets github personal-access-token
  devops config secrets AWS_ACCESS_KEY_ID
  devops config secrets --interactive
  devops config secrets -i aws
  devops config secrets --verbose aws dev iam-access-key
  devops config secrets --name aws-dev --tag iam-access-key
  devops config secrets --name aws-dev --tag session-token
  devops config secrets --path ~/private/team-secrets.json aws dev
  devops config secrets --edit

Terms are case-insensitive substring matches. All terms must match somewhere across entry
name/tags/profile, secret name/tags/scopes, metadata, notes, or env var keys.
Use --interactive/-i to choose from matching entries with the TV fuzzy picker.
Use --verbose/-v to print the selected bundle and env var keys without secret values.
Exact selectors are case-sensitive and can be combined with terms for script-stable matching.
"""


def secrets(
    terms: Annotated[
        list[str] | None,
        typer.Argument(
            help=(
                "Case-insensitive terms used to select one secret bundle. All terms must match across entry name/tags/profile, "
                "secret name/tags/scopes, metadata, notes, or env var keys."
            )
        ),
    ] = None,
    secrets_path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Path to a secrets JSON file. Defaults to .stackops/secrets/secrets.json in the current directory."),
    ] = None,
    edit: Annotated[bool, typer.Option("--edit", "-e", help="Open the secrets JSON file for editing instead of loading env vars.")] = False,
    editor: Annotated[str, typer.Option("--editor", help="Editor to use with --edit. Defaults to hx.")] = "hx",
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive",
            "--interative",
            "-i",
            help="Choose the secret bundle with a TV fuzzy picker. Terms and exact selectors pre-filter the list.",
        ),
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Print the selected secret bundle and env var keys without secret values.")
    ] = False,
    entry_name: Annotated[
        str | None,
        typer.Option("--name", "-n", help="Exact entries[].name value to require. Use with --tag/--key when an entry has multiple secrets."),
    ] = None,
    secret_name: Annotated[str | None, typer.Option("--secret-name", help="Exact entries[].secrets[].name value to require.")] = None,
    tags: Annotated[
        list[str] | None, typer.Option("--tag", "--tags", "-t", help="Exact entry or secret tag to require. Repeat for multiple tags.")
    ] = None,
    entry_tags: Annotated[
        list[str] | None, typer.Option("--entry-tag", help="Exact entries[].tags value to require. Repeat for multiple tags.")
    ] = None,
    secret_tags: Annotated[
        list[str] | None, typer.Option("--secret-tag", help="Exact entries[].secrets[].tags value to require. Repeat for multiple tags.")
    ] = None,
    scopes: Annotated[
        list[str] | None, typer.Option("--scope", help="Exact entries[].secrets[].scopes value to require. Repeat for multiple scopes.")
    ] = None,
    keys: Annotated[
        list[str] | None, typer.Option("--key", "-k", help="Exact env var key in keyValues to require. Repeat for multiple keys.")
    ] = None,
) -> None:
    """🔐 <S> Define env vars from .stackops/secrets/secrets.json."""
    resolved_secrets_path = _resolve_secrets_path(secrets_path)
    if edit:
        _edit_secrets_file(secrets_path=resolved_secrets_path, editor=editor)
        return

    candidates = load_secret_candidates(resolved_secrets_path)
    selectors = SecretSelectors(
        entry_name=_clean_optional_selector(entry_name),
        secret_name=_clean_optional_selector(secret_name),
        tags=_clean_selector_values(tags),
        entry_tags=_clean_selector_values(entry_tags),
        secret_tags=_clean_selector_values(secret_tags),
        scopes=_clean_selector_values(scopes),
        keys=_clean_selector_values(keys),
    )
    candidate = resolve_candidate(candidates=candidates, terms=terms, selectors=selectors, interactive=interactive)
    _validate_env_names(candidate.key_values)
    _write_env_handoff(candidate.key_values)
    if verbose:
        _echo_verbose_selection(candidate=candidate, secrets_path=resolved_secrets_path)

    names = ", ".join(candidate.key_values)
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Prepared {len(candidate.key_values)} env variable(s)"
    if names:
        msg += f": {names}"
    else:
        msg += "."
    typer.echo(msg)


def _resolve_secrets_path(secrets_path: Path | None) -> Path:
    if secrets_path is None:
        return Path.cwd() / SECRETS_RELATIVE_PATH
    expanded_path = secrets_path.expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return Path.cwd() / expanded_path


def _edit_secrets_file(secrets_path: Path, editor: str) -> None:
    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    if not secrets_path.exists():
        secrets_path.write_text(_read_default_secrets_template(), encoding="utf-8")
        _write_default_secrets_schema(secrets_path.parent / "secrets.schema.json")

    editor_bin = shutil.which(editor)
    if editor_bin is None:
        _fail(f"Editor '{editor}' is not available on PATH.")

    result = subprocess.run([editor_bin, str(secrets_path)], check=False)
    if result.returncode != 0:
        _fail(f"Editor exited with status code {result.returncode}.")


def _read_default_secrets_template() -> str:
    import stackops.utils.schemas.secrets as secrets_assets

    from stackops.utils.path_reference import get_path_reference_path

    template_path = get_path_reference_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE)
    return template_path.read_text(encoding="utf-8")


def _write_default_secrets_schema(schema_path: Path) -> None:
    if schema_path.exists():
        return

    import stackops.utils.schemas.secrets as secrets_assets

    from stackops.utils.path_reference import get_path_reference_path

    source_path = get_path_reference_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE)
    schema_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")


def _clean_optional_selector(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _clean_selector_values(values: list[str] | None) -> tuple[str, ...]:
    return tuple(stripped_value for value in values or () if (stripped_value := value.strip()))


def _validate_env_names(key_values: Mapping[str, SecretJsonValue]) -> None:
    invalid_names = [name for name in key_values if ENV_VAR_NAME_RE.fullmatch(name) is None]
    if invalid_names:
        names = ", ".join(invalid_names)
        _fail(f"Invalid environment variable name(s) in keyValues: {names}")


def _echo_verbose_selection(*, candidate: SecretCandidate, secrets_path: Path) -> None:
    typer.echo("Selected secret bundle:")
    typer.echo(f"  Bundle: {_candidate_verbose_label(candidate)}")
    typer.echo(f"  Source: {secrets_path}")
    typer.echo(f"  JSON path: {candidate.json_path}")
    typer.echo(f"  Entry tags: {_join_display(candidate.entry_tags)}")
    typer.echo(f"  Secret tags: {_join_display(candidate.secret_tags)}")
    typer.echo(f"  Scopes: {_join_display(candidate.scopes)}")
    typer.echo("Defining env vars:")
    for key in candidate.key_values:
        typer.echo(f"  {key}")


def _candidate_verbose_label(candidate: SecretCandidate) -> str:
    secret_label = candidate.secret_name
    if secret_label is None and candidate.secret_tags:
        secret_label = ",".join(candidate.secret_tags)
    if secret_label is None:
        secret_label = "<unnamed secret>"
    return f"{candidate.entry_name} / {secret_label}"


def _join_display(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def _write_env_handoff(key_values: Mapping[str, SecretJsonValue]) -> None:
    op_program_path_raw = os.environ.get("OP_PROGRAM_PATH")
    if not op_program_path_raw:
        _fail("Cannot define env variables in the parent shell because OP_PROGRAM_PATH is not set. Run through the StackOps shell wrapper.")

    op_program_path = Path(op_program_path_raw)
    if op_program_path.exists():
        _fail(f"Cannot write shell handoff script because OP_PROGRAM_PATH already exists: {op_program_path}")

    op_program_path.parent.mkdir(parents=True, exist_ok=True)

    powershell = platform.system() == "Windows"
    env_suffix = ".secrets.env.ps1" if powershell else ".secrets.env.sh"
    env_path = op_program_path.with_name(f"{op_program_path.stem}{env_suffix}")
    if env_path.exists():
        _fail(f"Cannot write secrets env file because it already exists: {env_path}")

    env_path.write_text(_render_env_file(key_values=key_values, powershell=powershell), encoding="utf-8")
    _chmod_private(env_path, 0o600)

    op_program_path.write_text(_render_loader_file(env_path=env_path, powershell=powershell), encoding="utf-8")
    _chmod_private(op_program_path, 0o700)


def _render_env_file(key_values: Mapping[str, SecretJsonValue], powershell: bool) -> str:
    if powershell:
        lines = ["# StackOps secrets env file. This file is removed after loading."]
        for key, value in key_values.items():
            lines.append(f"$env:{key} = {_quote_powershell(render_secret_value(value))}")
        return "\n".join(lines) + "\n"

    lines = ["# StackOps secrets env file. This file is removed after loading.", "set +x"]
    for key, value in key_values.items():
        lines.append(f"export {key}={shlex.quote(render_secret_value(value))}")
    return "\n".join(lines) + "\n"


def _render_loader_file(env_path: Path, powershell: bool) -> str:
    if powershell:
        env_path_quoted = _quote_powershell(str(env_path))
        return f"""# StackOps secrets loader. Secret values live in a private temp file, not here.
$StackOpsSecretEnvFile = {env_path_quoted}
if (-not (Test-Path -LiteralPath $StackOpsSecretEnvFile)) {{
    Write-Error "StackOps secrets env file is missing: $StackOpsSecretEnvFile"
    exit 1
}}
. $StackOpsSecretEnvFile
Remove-Item -LiteralPath $StackOpsSecretEnvFile -Force -ErrorAction SilentlyContinue
Remove-Variable -Name StackOpsSecretEnvFile -ErrorAction SilentlyContinue
"""

    env_path_quoted = shlex.quote(str(env_path))
    return f"""# StackOps secrets loader. Secret values live in a private temp file, not here.
_stackops_secret_env_file={env_path_quoted}
if [ ! -f "$_stackops_secret_env_file" ]; then
  echo "StackOps secrets env file is missing: $_stackops_secret_env_file" >&2
  return 1 2>/dev/null || exit 1
fi
case $- in
  *x*) _stackops_restore_xtrace=1; set +x ;;
  *) _stackops_restore_xtrace=0 ;;
esac
. "$_stackops_secret_env_file"
rm -f "$_stackops_secret_env_file"
if [ "$_stackops_restore_xtrace" = "1" ]; then
  set -x
fi
unset _stackops_secret_env_file _stackops_restore_xtrace
"""


def _quote_powershell(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _chmod_private(path: Path, mode: int) -> None:
    if platform.system() == "Windows":
        return
    path.chmod(mode)


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)
