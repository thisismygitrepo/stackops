"""Search StackOps secrets with exact selectors only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

from stackops.utils.schemas.secrets.secrets_loader import SecretsSchemaError, load_secrets_file
from stackops.utils.schemas.secrets.secrets_types import (
    SecretRecord,
    SecretRotation,
    SecretsEntry,
    SecretValueMap,
)

DEFAULT_SECRETS_PATH = Path(".stackops") / "secrets" / "secrets.json"

__all__ = [
    "DEFAULT_SECRETS_PATH",
    "Entry",
    "SecretValueMap",
    "StackOpsSecretsError",
    "SecretsFileError",
    "render_secret_value",
    "search_secrets",
]


Entry: TypeAlias = SecretsEntry


class StackOpsSecretsError(Exception):
    """Base exception for the Python secrets API."""


class SecretsFileError(StackOpsSecretsError, ValueError):
    """Raised when the secrets file does not match the strict schema."""


def render_secret_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def search_secrets(
    *,
    path: str | Path | None = None,
    entry_name: str | None = None,
    profile: str | None = None,
    secret_name: str | None = None,
    tags: tuple[str, ...] = (),
    entry_tags: tuple[str, ...] = (),
    secret_tags: tuple[str, ...] = (),
    scopes: tuple[str, ...] = (),
    keys: tuple[str, ...] = (),
) -> list[Entry]:
    """Return schema-shaped entries whose secret bundles match exact selectors."""
    try:
        secrets_file = load_secrets_file(_resolve_path(path))
    except SecretsSchemaError as exc:
        raise SecretsFileError(str(exc)) from exc

    entries: list[Entry] = []
    for entry in secrets_file["entries"]:
        for secret in entry["secrets"]:
            if _secret_matches(
                entry=entry,
                secret=secret,
                entry_name=entry_name,
                profile=profile,
                secret_name=secret_name,
                tags=tags,
                entry_tags=entry_tags,
                secret_tags=secret_tags,
                scopes=scopes,
                keys=keys,
            ):
                entries.append(_entry_with_secret(entry=entry, secret=secret))
    return entries


def _resolve_path(path: str | Path | None) -> Path:
    if path is None:
        return Path.cwd() / DEFAULT_SECRETS_PATH

    expanded_path = Path(path).expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return Path.cwd() / expanded_path


def _secret_matches(
    *,
    entry: SecretsEntry,
    secret: SecretRecord,
    entry_name: str | None,
    profile: str | None,
    secret_name: str | None,
    tags: tuple[str, ...],
    entry_tags: tuple[str, ...],
    secret_tags: tuple[str, ...],
    scopes: tuple[str, ...],
    keys: tuple[str, ...],
) -> bool:
    current_entry_tags = tuple(entry.get("tags", ()))
    current_secret_tags = tuple(secret["tags"])
    current_scopes = tuple(secret["scopes"])
    current_keys = tuple(secret["keyValues"])

    if entry_name is not None and entry["name"] != entry_name:
        return False
    if profile is not None and entry.get("profile") != profile:
        return False
    if secret_name is not None and secret.get("name") != secret_name:
        return False
    if not all(tag in current_entry_tags or tag in current_secret_tags for tag in tags):
        return False
    if not all(tag in current_entry_tags for tag in entry_tags):
        return False
    if not all(tag in current_secret_tags for tag in secret_tags):
        return False
    if not all(scope in current_scopes for scope in scopes):
        return False
    return all(key in current_keys for key in keys)


def _entry_with_secret(*, entry: SecretsEntry, secret: SecretRecord) -> Entry:
    matched_entry: Entry = {"name": entry["name"], "secrets": [_copy_secret(secret)]}
    if "tags" in entry:
        matched_entry["tags"] = list(entry["tags"])
    if "description" in entry:
        matched_entry["description"] = entry["description"]
    if "url" in entry:
        matched_entry["url"] = entry["url"]
    if "email" in entry:
        matched_entry["email"] = entry["email"]
    if "username" in entry:
        matched_entry["username"] = entry["username"]
    if "profile" in entry:
        matched_entry["profile"] = entry["profile"]
    if "metadata" in entry:
        matched_entry["metadata"] = dict(entry["metadata"])
    return matched_entry


def _copy_secret(secret: SecretRecord) -> SecretRecord:
    copied_secret: SecretRecord = {
        "tags": list(secret["tags"]),
        "scopes": list(secret["scopes"]),
        "keyValues": dict(secret["keyValues"]),
    }
    if "name" in secret:
        copied_secret["name"] = secret["name"]
    if "description" in secret:
        copied_secret["description"] = secret["description"]
    if "rotation" in secret:
        copied_secret["rotation"] = _copy_rotation(secret["rotation"])
    if "metadata" in secret:
        copied_secret["metadata"] = dict(secret["metadata"])
    if "notes" in secret:
        copied_secret["notes"] = secret["notes"]
    return copied_secret


def _copy_rotation(rotation: SecretRotation) -> SecretRotation:
    copied_rotation: SecretRotation = {}
    if "lastRotated" in rotation:
        copied_rotation["lastRotated"] = rotation["lastRotated"]
    if "rotateEveryDays" in rotation:
        copied_rotation["rotateEveryDays"] = rotation["rotateEveryDays"]
    if "owner" in rotation:
        copied_rotation["owner"] = rotation["owner"]
    return copied_rotation
