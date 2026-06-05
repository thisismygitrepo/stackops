import json
from pathlib import Path
from typing import Any, Mapping, NoReturn

from stackops.utils.schemas.secrets.secrets_types import (
    Login,
    SecretRecord,
    SecretRotation,
    SecretStringMap,
    SecretsFile,
    SecretValueMap,
)


class SecretsSchemaError(ValueError):
    pass


def load_secrets_file(secrets_path: Path) -> SecretsFile:
    if not secrets_path.exists():
        _fail(f"Secrets file not found: {secrets_path}")

    try:
        payload = json.loads(secrets_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"Invalid JSON in {secrets_path}: {exc.msg} at line {exc.lineno}, column {exc.colno}.")

    if not isinstance(payload, Mapping):
        _fail(f"Secrets file must contain a JSON object: {secrets_path}")

    return _parse_secrets_file(payload=payload, secrets_path=secrets_path)


def _parse_secrets_file(*, payload: Mapping[str, Any], secrets_path: Path) -> SecretsFile:
    _reject_unknown_keys(payload, allowed_keys=("$schema", "version", "entries"), path=str(secrets_path))
    schema = _optional_string(payload.get("$schema"), "$schema")
    version = _string_value(payload.get("version"), "version")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        _fail(f"Secrets file must define an entries array: {secrets_path}")
    if not entries:
        _fail(f"Secrets file entries array must define at least one login: {secrets_path}")

    parsed_entries: list[Login] = []
    for entry_index, entry_raw in enumerate(entries):
        if not isinstance(entry_raw, Mapping):
            _fail(f"Invalid secrets login at entries[{entry_index}]: expected object.")
        parsed_entries.append(_parse_entry(entry=entry_raw, entry_index=entry_index))

    secrets_file: SecretsFile = {"version": version, "entries": parsed_entries}
    if schema is not None:
        secrets_file["$schema"] = schema
    return secrets_file


def _parse_entry(entry: Mapping[str, Any], entry_index: int) -> Login:
    entry_path = f"entries[{entry_index}]"
    _reject_unknown_keys(
        entry,
        allowed_keys=("name", "tags", "description", "notes", "url", "email", "username", "profile", "secrets", "metadata"),
        path=entry_path,
    )
    secrets_raw = entry.get("secrets")
    if not isinstance(secrets_raw, list):
        _fail(f"Invalid secrets login at {entry_path}.secrets: expected array.")
    if not secrets_raw:
        _fail(f"Invalid secrets login at {entry_path}.secrets: expected at least one secret.")

    parsed_secrets: list[SecretRecord] = []
    for secret_index, secret_raw in enumerate(secrets_raw):
        if not isinstance(secret_raw, Mapping):
            _fail(f"Invalid secret at entries[{entry_index}].secrets[{secret_index}]: expected object.")
        parsed_secrets.append(_parse_secret(secret=secret_raw, entry_index=entry_index, secret_index=secret_index))

    parsed_entry: Login = {
        "name": _string_value(entry.get("name"), f"entries[{entry_index}].name"),
        "secrets": parsed_secrets,
    }
    tags = _optional_string_list(entry.get("tags"), f"entries[{entry_index}].tags")
    if tags is not None:
        parsed_entry["tags"] = tags
    description = _optional_string(entry.get("description"), f"entries[{entry_index}].description")
    if description is not None:
        parsed_entry["description"] = description
    notes = _optional_string(entry.get("notes"), f"entries[{entry_index}].notes")
    if notes is not None:
        parsed_entry["notes"] = notes
    url = _optional_string(entry.get("url"), f"entries[{entry_index}].url")
    if url is not None:
        parsed_entry["url"] = url
    email = _optional_string(entry.get("email"), f"entries[{entry_index}].email")
    if email is not None:
        parsed_entry["email"] = email
    username = _optional_string(entry.get("username"), f"entries[{entry_index}].username")
    if username is not None:
        parsed_entry["username"] = username
    profile = _optional_string(entry.get("profile"), f"entries[{entry_index}].profile")
    if profile is not None:
        parsed_entry["profile"] = profile
    metadata = _optional_string_map(entry.get("metadata"), f"entries[{entry_index}].metadata")
    if metadata is not None:
        parsed_entry["metadata"] = metadata
    return parsed_entry


def _parse_secret(secret: Mapping[str, Any], entry_index: int, secret_index: int) -> SecretRecord:
    secret_path = f"entries[{entry_index}].secrets[{secret_index}]"
    _reject_unknown_keys(
        secret,
        allowed_keys=("name", "tags", "description", "scopes", "keyValues", "rotation", "metadata"),
        path=secret_path,
    )
    tags = _optional_string_list(secret.get("tags"), f"{secret_path}.tags")
    scopes = _string_list(secret["scopes"], f"{secret_path}.scopes") if "scopes" in secret else []
    parsed_secret: SecretRecord = {
        "tags": tags if tags is not None else [],
        "scopes": scopes,
        "keyValues": _key_values(secret.get("keyValues"), f"{secret_path}.keyValues"),
    }
    name = _optional_string(secret.get("name"), f"{secret_path}.name")
    if name is not None:
        parsed_secret["name"] = name
    description = _optional_string(secret.get("description"), f"{secret_path}.description")
    if description is not None:
        parsed_secret["description"] = description
    rotation = _optional_rotation(secret.get("rotation"), f"{secret_path}.rotation")
    if rotation is not None:
        parsed_secret["rotation"] = rotation
    metadata = _optional_string_map(secret.get("metadata"), f"{secret_path}.metadata")
    if metadata is not None:
        parsed_secret["metadata"] = metadata
    return parsed_secret


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


def _optional_string_list(value: Any, path: str) -> list[str] | None:
    if value is None:
        return None
    return _string_list(value, path)


def _string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list):
        _fail(f"Invalid secrets file: {path} must be an array of strings when present.")
    values: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            _fail(f"Invalid secrets file: {path}[{index}] must be a non-empty string.")
        values.append(item)
    return values


def _optional_string_map(value: Any, path: str) -> SecretStringMap | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        _fail(f"Invalid secrets file: {path} must be an object.")

    string_map: SecretStringMap = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            _fail(f"Invalid secrets file: {path} contains a non-string or empty key.")
        if not isinstance(item, str) or not item.strip():
            _fail(f"Invalid secrets file: {path}.{key} must be a non-empty string.")
        string_map[key] = item
    return string_map


def _optional_rotation(value: Any, path: str) -> SecretRotation | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        _fail(f"Invalid secrets file: {path} must be an object.")
    _reject_unknown_keys(value, allowed_keys=("lastRotated", "rotateEveryDays", "owner"), path=path)

    rotation: SecretRotation = {}
    last_rotated = _optional_string(value.get("lastRotated"), f"{path}.lastRotated")
    if last_rotated is not None:
        rotation["lastRotated"] = last_rotated

    rotate_every_days = value.get("rotateEveryDays")
    if rotate_every_days is not None:
        if isinstance(rotate_every_days, bool) or not isinstance(rotate_every_days, int) or rotate_every_days < 1:
            _fail(f"Invalid secrets file: {path}.rotateEveryDays must be an integer greater than or equal to 1.")
        rotation["rotateEveryDays"] = rotate_every_days

    owner = _optional_string(value.get("owner"), f"{path}.owner")
    if owner is not None:
        rotation["owner"] = owner
    return rotation


def _key_values(value: Any, path: str) -> SecretValueMap:
    if not isinstance(value, Mapping):
        _fail(f"Invalid secrets file: {path} must be an object.")

    key_values: SecretValueMap = {}
    for key, secret_value in value.items():
        if not isinstance(key, str):
            _fail(f"Invalid secrets file: {path} contains a non-string key.")
        key_values[key] = _json_value(secret_value, _json_field_path(path, key))
    return key_values


def _json_value(value: Any, path: str) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        items: list[object] = []
        for index, item in enumerate(value):
            items.append(_json_value(item, f"{path}[{index}]"))
        return items
    if isinstance(value, Mapping):
        mapping_value: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                _fail(f"Invalid secrets file: {path} contains a non-string key.")
            mapping_value[key] = _json_value(item, _json_field_path(path, key))
        return mapping_value
    _fail(f"Invalid secrets file: {path} must be a JSON value.")


def _json_field_path(path: str, key: str) -> str:
    return f"{path}[{json.dumps(key)}]"


def _reject_unknown_keys(mapping: Mapping[str, Any], *, allowed_keys: tuple[str, ...], path: str) -> None:
    unknown_keys = [key for key in mapping if key not in allowed_keys]
    if unknown_keys:
        keys = ", ".join(str(key) for key in unknown_keys)
        _fail(f"Invalid secrets file: {path} contains unknown key(s): {keys}.")


def _fail(message: str) -> NoReturn:
    raise SecretsSchemaError(message)
