from collections.abc import Mapping

import typer

from stackops.secrets.models import Login, SecretRecord, SecretRotation, SecretStringMap, SecretValueMap


def prompt_secret_login() -> Login:
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
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_actions import is_valid_env_name

    while True:
        key = _prompt_required_string("Env var key")
        if not is_valid_env_name(key):
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
