import json
import os
import platform
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Mapping, NoReturn

import typer

from stackops.secrets import render_secret_value
from stackops.utils.schemas.secrets.secrets_loader import SecretsSchemaError, load_secrets_file
from stackops.utils.schemas.secrets.secrets_types import Login, SecretRecord, SecretRotation, SecretStringMap, SecretValueMap

SECRETS_SCHEMA_FILENAME = "secrets.schema.json"
SECRETS_FILE_VERSION = "0.5"
ENV_VAR_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _edit_secrets_file(
    secrets_path: Path,
    editor: str,
    *,
    create: bool = False,
    shutil_module=shutil,
    subprocess_module=subprocess,
) -> None:
    if not secrets_path.exists():
        if not create:
            _fail(f"Secrets file not found: {secrets_path}. Pass --create with --edit to create it from the packaged example.")
        secrets_path.parent.mkdir(parents=True, exist_ok=True)
        secrets_path.write_text(_read_default_secrets_template(), encoding="utf-8")
        _write_default_secrets_schema(secrets_path.parent / SECRETS_SCHEMA_FILENAME)
    elif create:
        _write_default_secrets_schema(secrets_path.parent / SECRETS_SCHEMA_FILENAME)

    editor_bin = shutil_module.which(editor)
    if editor_bin is None:
        _fail(f"Editor '{editor}' is not available on PATH.")

    result = subprocess_module.run([editor_bin, str(secrets_path)], check=False)
    if result.returncode != 0:
        _fail(f"Editor exited with status code {result.returncode}.")


def _add_secrets_entry(
    secrets_path: Path,
    *,
    create: bool = False,
    prompt_secret_login_entry: Callable[[], Login] | None = None,
) -> None:
    secrets_file, created_file = _load_or_initialize_add_target(secrets_path=secrets_path, create=create)
    prompt_entry = prompt_secret_login_entry or _prompt_secret_login_entry
    entry = prompt_entry()
    _secrets_entries(secrets_file).append(entry)
    _write_secrets_file(secrets_path=secrets_path, secrets_file=secrets_file, created_file=created_file)
    if create:
        _write_default_secrets_schema(secrets_path.parent / SECRETS_SCHEMA_FILENAME)

    typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Added secrets entry '{entry['name']}' to {secrets_path}")


def _load_or_initialize_add_target(*, secrets_path: Path, create: bool) -> tuple[dict[str, object], bool]:
    if not secrets_path.exists():
        if not create:
            _fail(f"Secrets file not found: {secrets_path}. Pass --create with --add to create it.")
        return {"$schema": f"./{SECRETS_SCHEMA_FILENAME}", "version": SECRETS_FILE_VERSION, "entries": []}, True

    try:
        load_secrets_file(secrets_path)
    except SecretsSchemaError as exc:
        _fail(str(exc))

    return _read_secrets_json_payload(secrets_path), False


def _read_secrets_json_payload(secrets_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(secrets_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"Invalid JSON in {secrets_path}: {exc.msg} at line {exc.lineno}, column {exc.colno}.")
    if not isinstance(payload, dict):
        _fail(f"Secrets file must contain a JSON object: {secrets_path}")
    _secrets_entries(payload)
    return payload


def _secrets_entries(secrets_file: Mapping[str, object]) -> list[object]:
    entries = secrets_file.get("entries")
    if not isinstance(entries, list):
        _fail("Secrets file must define an entries array.")
    return entries


def _write_secrets_file(*, secrets_path: Path, secrets_file: Mapping[str, object], created_file: bool) -> None:
    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    secrets_path.write_text(json.dumps(secrets_file, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if created_file:
        _chmod_private(secrets_path, 0o600)


def _prompt_secret_login_entry() -> Login:
    typer.echo("Login entry")
    entry: Login = {"name": _prompt_required_string("Login name"), "secrets": []}
    tags = _prompt_string_list("Login tags")
    if tags:
        entry["tags"] = tags
    description = _prompt_optional_string("Login description")
    if description is not None:
        entry["description"] = description
    url = _prompt_optional_string("Login URL")
    if url is not None:
        entry["url"] = url
    email = _prompt_optional_string("Login email")
    if email is not None:
        entry["email"] = email
    username = _prompt_optional_string("Login username")
    if username is not None:
        entry["username"] = username
    account_name = _prompt_optional_string("Login accountName")
    if account_name is not None:
        entry["accountName"] = account_name
    metadata = _prompt_string_map("login")
    if metadata:
        entry["metadata"] = metadata

    while True:
        entry["secrets"].append(_prompt_secret_record(secret_number=len(entry["secrets"]) + 1))
        if not typer.confirm("Add another secret bundle?", default=False):
            break
    return entry


def _prompt_secret_record(*, secret_number: int) -> SecretRecord:
    typer.echo(f"Secret bundle {secret_number}")
    name = _prompt_required_string("Secret name")
    tags = _prompt_string_list("Secret tags")
    scopes = _prompt_string_list("Secret scopes")
    secret: SecretRecord = {
        "name": name,
        "tags": tags,
        "scopes": scopes,
        "keyValues": _prompt_secret_key_values(),
    }
    description = _prompt_optional_string("Secret description")
    if description is not None:
        secret["description"] = description
    rotation = _prompt_secret_rotation()
    if rotation:
        secret["rotation"] = rotation
    metadata = _prompt_string_map("secret")
    if metadata:
        secret["metadata"] = metadata
    return secret


def _prompt_secret_key_values() -> SecretValueMap:
    typer.echo("Secret keyValues")
    key_values: SecretValueMap = {}
    while True:
        key = _prompt_env_key(existing_keys=key_values)
        key_values[key] = typer.prompt(f"Value for {key}", default="", hide_input=True, show_default=False)
        if not typer.confirm("Add another keyValue?", default=False):
            break
    return key_values


def _prompt_secret_rotation() -> SecretRotation | None:
    if not typer.confirm("Add rotation metadata?", default=False):
        return None

    rotation: SecretRotation = {}
    last_rotated = _prompt_optional_string("Rotation lastRotated")
    if last_rotated is not None:
        rotation["lastRotated"] = last_rotated
    rotate_every_days = _prompt_optional_positive_int("Rotation rotateEveryDays")
    if rotate_every_days is not None:
        rotation["rotateEveryDays"] = rotate_every_days
    owner = _prompt_optional_string("Rotation owner")
    if owner is not None:
        rotation["owner"] = owner
    return rotation or None


def _prompt_string_map(label: str) -> SecretStringMap | None:
    if not typer.confirm(f"Add {label} metadata?", default=False):
        return None

    values: SecretStringMap = {}
    while True:
        key = _prompt_optional_string(f"{label.title()} metadata key")
        if key is None:
            if values or typer.confirm(f"Continue without {label} metadata?", default=True):
                break
            continue
        values[key] = _prompt_required_string(f"{label.title()} metadata value")
        if not typer.confirm(f"Add another {label} metadata field?", default=False):
            break
    return values or None


def _prompt_env_key(*, existing_keys: Mapping[str, object]) -> str:
    while True:
        key = _prompt_required_string("Env var key")
        if ENV_VAR_NAME_RE.fullmatch(key) is None:
            typer.echo("Use a shell-compatible env var key, for example API_TOKEN.")
            continue
        if key in existing_keys:
            typer.echo(f"Env var key already exists in this bundle: {key}")
            continue
        return key


def _prompt_required_string(label: str) -> str:
    while True:
        value = str(typer.prompt(label, default="", show_default=False)).strip()
        if value:
            return value
        typer.echo(f"{label} is required.")


def _prompt_optional_string(label: str) -> str | None:
    value = str(typer.prompt(f"{label} (optional)", default="", show_default=False)).strip()
    return value or None


def _prompt_string_list(label: str) -> list[str]:
    while True:
        raw_value = str(typer.prompt(f"{label} (comma-separated, optional)", default="", show_default=False))
        values = [value.strip() for value in raw_value.split(",") if value.strip()]
        if len(values) == len(set(values)):
            return values
        typer.echo(f"{label} must not contain duplicate values.")


def _prompt_optional_positive_int(label: str) -> int | None:
    while True:
        raw_value = _prompt_optional_string(label)
        if raw_value is None:
            return None
        try:
            value = int(raw_value)
        except ValueError:
            typer.echo(f"{label} must be an integer greater than or equal to 1.")
            continue
        if value >= 1:
            return value
        typer.echo(f"{label} must be an integer greater than or equal to 1.")


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


def _validate_env_names(key_values: Mapping[str, object]) -> None:
    invalid_names = [name for name in key_values if ENV_VAR_NAME_RE.fullmatch(name) is None]
    if invalid_names:
        names = ", ".join(invalid_names)
        _fail(f"Invalid environment variable name(s) in keyValues: {names}")


def _write_env_handoff(key_values: Mapping[str, object]) -> None:
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


def _render_env_file(key_values: Mapping[str, object], powershell: bool) -> str:
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
