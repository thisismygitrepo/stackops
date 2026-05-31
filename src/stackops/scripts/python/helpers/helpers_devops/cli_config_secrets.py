import json
import os
import platform
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Mapping, NoReturn, cast

import typer

SECRETS_RELATIVE_PATH = Path(".stackops") / "secrets" / "secrets.json"
ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class SecretCandidate:
    entry_name: str
    entry_tags: tuple[str, ...]
    secret_name: str | None
    secret_tags: tuple[str, ...]
    scopes: tuple[str, ...]
    key_values: dict[str, str]
    searchable_values: tuple[str, ...]


def secrets(
    queries: Annotated[list[str] | None, typer.Argument(help="Terms used to identify exactly one secrets keyValues entry.")] = None,
    secrets_path: Annotated[
        Path | None,
        typer.Option("--path", "-p", help="Path to a secrets JSON file. Defaults to .stackops/secrets/secrets.json in the current directory."),
    ] = None,
    edit: Annotated[bool, typer.Option("--edit", "-e", help="Open the secrets JSON file for editing instead of loading env vars.")] = False,
    editor: Annotated[str, typer.Option("--editor", help="Editor to use with --edit. Defaults to hx.")] = "hx",
) -> None:
    """🔐 <S> Define env vars from .stackops/secrets/secrets.json."""
    resolved_secrets_path = _resolve_secrets_path(secrets_path)
    if edit:
        _edit_secrets_file(secrets_path=resolved_secrets_path, editor=editor)
        return

    candidates = _load_secret_candidates(resolved_secrets_path)
    candidate = _resolve_candidate(candidates=candidates, queries=queries)
    _validate_env_names(candidate.key_values)
    _write_env_handoff(candidate.key_values)

    names = ", ".join(candidate.key_values)
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Prepared {len(candidate.key_values)} env variable(s): {names}"
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


def _load_secret_candidates(secrets_path: Path) -> list[SecretCandidate]:
    if not secrets_path.exists():
        _fail(f"Secrets file not found: {secrets_path}")

    try:
        payload = json.loads(secrets_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"Invalid JSON in {secrets_path}: {exc.msg} at line {exc.lineno}, column {exc.colno}.")

    if not isinstance(payload, Mapping):
        _fail(f"Secrets file must contain a JSON object: {secrets_path}")

    entries = payload.get("entries")
    if not isinstance(entries, list):
        _fail(f"Secrets file must define an entries array: {secrets_path}")
    entries_list = cast(list[Any], entries)

    candidates: list[SecretCandidate] = []
    for entry_index, entry_raw in enumerate(entries_list):
        if not isinstance(entry_raw, Mapping):
            _fail(f"Invalid secrets entry at entries[{entry_index}]: expected object.")
        candidates.extend(_entry_candidates(entry=entry_raw, entry_index=entry_index))

    if not candidates:
        _fail(f"No keyValues entries found in {secrets_path}")
    return candidates


def _entry_candidates(entry: Mapping[str, Any], entry_index: int) -> list[SecretCandidate]:
    entry_name = _string_value(entry.get("name"), f"entries[{entry_index}].name")
    entry_tags = _string_tuple(entry.get("tags"), f"entries[{entry_index}].tags")
    secrets_raw = entry.get("secrets")
    if not isinstance(secrets_raw, list):
        _fail(f"Invalid secrets entry at entries[{entry_index}].secrets: expected array.")
    secrets = cast(list[Any], secrets_raw)

    shared_search_values = _search_values_from_entry(entry=entry, entry_name=entry_name, entry_tags=entry_tags)

    candidates: list[SecretCandidate] = []
    for secret_index, secret_raw in enumerate(secrets):
        if not isinstance(secret_raw, Mapping):
            _fail(f"Invalid secret at entries[{entry_index}].secrets[{secret_index}]: expected object.")

        key_values_path = f"entries[{entry_index}].secrets[{secret_index}].keyValues"
        key_values = _key_values(secret_raw.get("keyValues"), key_values_path)
        secret_name = _optional_string(secret_raw.get("name"), f"entries[{entry_index}].secrets[{secret_index}].name")
        secret_tags = _string_tuple(secret_raw.get("tag"), f"entries[{entry_index}].secrets[{secret_index}].tag")
        scopes = _scope_tuple(secret_raw.get("scope"), f"entries[{entry_index}].secrets[{secret_index}].scope")
        secret_search_values = _search_values_from_secret(
            secret=secret_raw, secret_name=secret_name, secret_tags=secret_tags, scopes=scopes, key_names=tuple(key_values)
        )
        candidates.append(
            SecretCandidate(
                entry_name=entry_name,
                entry_tags=entry_tags,
                secret_name=secret_name,
                secret_tags=secret_tags,
                scopes=scopes,
                key_values=key_values,
                searchable_values=shared_search_values + secret_search_values,
            )
        )
    return candidates


def _search_values_from_entry(entry: Mapping[str, Any], entry_name: str, entry_tags: tuple[str, ...]) -> tuple[str, ...]:
    values: list[str] = [entry_name, *entry_tags]
    for key in ("description", "url", "email", "username", "accountId", "profile"):
        value = entry.get(key)
        if isinstance(value, str):
            values.append(value)
    values.extend(_string_map_terms(entry.get("metadata")))
    return tuple(values)


def _search_values_from_secret(
    secret: Mapping[str, Any], secret_name: str | None, secret_tags: tuple[str, ...], scopes: tuple[str, ...], key_names: tuple[str, ...]
) -> tuple[str, ...]:
    values: list[str] = [*secret_tags, *scopes, *key_names]
    if secret_name is not None:
        values.append(secret_name)
    for key in ("description", "notes"):
        value = secret.get(key)
        if isinstance(value, str):
            values.append(value)
    values.extend(_string_map_terms(secret.get("metadata")))
    return tuple(values)


def _resolve_candidate(candidates: list[SecretCandidate], queries: list[str] | None) -> SecretCandidate:
    normalized_queries = tuple(query.casefold() for query in queries or () if query.strip())
    if not normalized_queries:
        _fail("Pass at least one term to identify a secrets keyValues entry.")

    matches = [candidate for candidate in candidates if _candidate_matches(candidate=candidate, queries=normalized_queries)]
    if len(matches) == 1:
        return matches[0]

    query_text = " ".join(queries or ())
    if not matches:
        typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"No keyValues entry matched query: {query_text}")
        _print_candidate_list("Available keyValues entries:", candidates)
    else:
        typer.echo(
            typer.style("Error: ", fg=typer.colors.RED)
            + f"Query did not identify a unique keyValues entry: {query_text} matched {len(matches)} entries."
        )
        _print_candidate_list("Matching keyValues entries:", matches)
    raise typer.Exit(code=1)


def _candidate_matches(candidate: SecretCandidate, queries: tuple[str, ...]) -> bool:
    searchable_values = tuple(value.casefold() for value in candidate.searchable_values)
    return all(any(query in searchable_value for searchable_value in searchable_values) for query in queries)


def _validate_env_names(key_values: Mapping[str, str]) -> None:
    invalid_names = [name for name in key_values if ENV_VAR_NAME_RE.fullmatch(name) is None]
    if invalid_names:
        names = ", ".join(invalid_names)
        _fail(f"Invalid environment variable name(s) in keyValues: {names}")


def _write_env_handoff(key_values: Mapping[str, str]) -> None:
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


def _render_env_file(key_values: Mapping[str, str], powershell: bool) -> str:
    if powershell:
        lines = ["# StackOps secrets env file. This file is removed after loading."]
        for key, value in key_values.items():
            lines.append(f"$env:{key} = {_quote_powershell(value)}")
        return "\n".join(lines) + "\n"

    lines = ["# StackOps secrets env file. This file is removed after loading.", "set +x"]
    for key, value in key_values.items():
        lines.append(f"export {key}={shlex.quote(value)}")
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


def _print_candidate_list(title: str, candidates: list[SecretCandidate]) -> None:
    typer.echo(title)
    for candidate in candidates[:10]:
        typer.echo(f"  - {_candidate_label(candidate)}")
    if len(candidates) > 10:
        typer.echo(f"  ... {len(candidates) - 10} more")


def _candidate_label(candidate: SecretCandidate) -> str:
    secret_label = candidate.secret_name
    if secret_label is None and candidate.secret_tags:
        secret_label = ",".join(candidate.secret_tags)
    if secret_label is None:
        secret_label = "<unnamed secret>"
    keys = ", ".join(candidate.key_values)
    return f"{candidate.entry_name} / {secret_label} -> {keys}"


def _string_value(value: Any, path: str) -> str:
    if isinstance(value, str) and value.strip():
        return value
    _fail(f"Invalid secrets file: {path} must be a non-empty string.")


def _optional_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value
    _fail(f"Invalid secrets file: {path} must be a non-empty string when present.")


def _string_tuple(value: Any, path: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        _fail(f"Invalid secrets file: {path} must be an array of strings when present.")
    values: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            _fail(f"Invalid secrets file: {path}[{index}] must be a non-empty string.")
        values.append(item)
    return tuple(values)


def _scope_tuple(value: Any, path: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str) and value.strip():
        return (value,)
    return _string_tuple(value, path)


def _key_values(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        _fail(f"Invalid secrets file: {path} must be an object.")

    key_values: dict[str, str] = {}
    for key, secret_value in value.items():
        if not isinstance(key, str) or not key.strip():
            _fail(f"Invalid secrets file: {path} contains a non-string or empty key.")
        if not isinstance(secret_value, str):
            _fail(f"Invalid secrets file: {path}.{key} must be a string.")
        key_values[key] = secret_value
    if not key_values:
        _fail(f"Invalid secrets file: {path} must define at least one value.")
    return key_values


def _string_map_terms(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ()
    terms: list[str] = []
    for key, item in value.items():
        if isinstance(key, str):
            terms.append(key)
        if isinstance(item, str):
            terms.append(item)
    return tuple(terms)


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)
