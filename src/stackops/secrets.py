"""Search StackOps secrets with exact selectors only."""

from __future__ import annotations

import json
from pathlib import Path

from stackops.utils.schemas.secrets.secrets_loader import SecretsSchemaError, load_secrets_file
from stackops.utils.schemas.secrets.secrets_types import Login, SecretRecord, SecretRotation, SecretValueMap

DEFAULT_LOCAL_SECRETS_PATH = Path(".stackops") / "secrets" / "secrets.json"


__all__ = ["DEFAULT_LOCAL_SECRETS_PATH", "Login", "SecretValueMap", "StackOpsSecretsError", "SecretsFileError", "render_secret_value", "search_logins"]


class StackOpsSecretsError(Exception):
    """Base exception for the Python secrets API."""


class SecretsFileError(StackOpsSecretsError, ValueError):
    """Raised when the secrets file does not match the strict schema."""


def render_secret_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def search_logins(
    *,
    path: str | Path | None = None,
    login_name: str | None = None,
    account_name: str | None = None,
    secret_name: str | None = None,
    tags: tuple[str, ...] = (),
    login_tags: tuple[str, ...] = (),
    secret_tags: tuple[str, ...] = (),
    scopes: tuple[str, ...] = (),
    keys: tuple[str, ...] = (),
) -> list[Login]:
    """Return schema-shaped logins whose secret bundles match exact selectors."""
    try:
        secrets_file = load_secrets_file(_resolve_path(path))
    except SecretsSchemaError as exc:
        raise SecretsFileError(str(exc)) from exc

    logins: list[Login] = []
    for login in secrets_file["entries"]:
        for secret in login["secrets"]:
            if _secret_matches(
                login=login,
                secret=secret,
                login_name=login_name,
                account_name=account_name,
                secret_name=secret_name,
                tags=tags,
                login_tags=login_tags,
                secret_tags=secret_tags,
                scopes=scopes,
                keys=keys,
            ):
                logins.append(_login_with_secret(login=login, secret=secret))
    return logins


def _resolve_path(path: str | Path | None) -> Path:
    if path is None:
        from stackops.utils.source_of_truth import SECRETS_DOFILE
        return SECRETS_DOFILE
        # return Path.cwd() / DEFAULT_SECRETS_PATH
    expanded_path = Path(path).expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return Path.cwd() / expanded_path


def _secret_matches(
    *,
    login: Login,
    secret: SecretRecord,
    login_name: str | None,
    account_name: str | None,
    secret_name: str | None,
    tags: tuple[str, ...],
    login_tags: tuple[str, ...],
    secret_tags: tuple[str, ...],
    scopes: tuple[str, ...],
    keys: tuple[str, ...],
) -> bool:
    current_login_tags = tuple(login.get("tags", ()))
    current_secret_tags = tuple(secret["tags"])
    current_scopes = tuple(secret["scopes"])
    current_keys = tuple(secret["keyValues"])

    if login_name is not None and login["name"] != login_name:
        return False
    if account_name is not None and login.get("accountName") != account_name:
        return False
    if secret_name is not None and secret["name"] != secret_name:
        return False
    if not all(tag in current_login_tags or tag in current_secret_tags for tag in tags):
        return False
    if not all(tag in current_login_tags for tag in login_tags):
        return False
    if not all(tag in current_secret_tags for tag in secret_tags):
        return False
    if not all(scope in current_scopes for scope in scopes):
        return False
    return all(key in current_keys for key in keys)


def _login_with_secret(*, login: Login, secret: SecretRecord) -> Login:
    matched_login: Login = {"name": login["name"], "secrets": [_copy_secret(secret)]}
    if "tags" in login:
        matched_login["tags"] = list(login["tags"])
    if "description" in login:
        matched_login["description"] = login["description"]
    if "url" in login:
        matched_login["url"] = login["url"]
    if "email" in login:
        matched_login["email"] = login["email"]
    if "username" in login:
        matched_login["username"] = login["username"]
    if "accountName" in login:
        matched_login["accountName"] = login["accountName"]
    if "metadata" in login:
        matched_login["metadata"] = dict(login["metadata"])
    return matched_login


def _copy_secret(secret: SecretRecord) -> SecretRecord:
    copied_secret: SecretRecord = {
        "name": secret["name"],
        "tags": list(secret["tags"]),
        "scopes": list(secret["scopes"]),
        "keyValues": dict(secret["keyValues"]),
    }
    if "description" in secret:
        copied_secret["description"] = secret["description"]
    if "rotation" in secret:
        copied_secret["rotation"] = _copy_rotation(secret["rotation"])
    if "metadata" in secret:
        copied_secret["metadata"] = dict(secret["metadata"])
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
