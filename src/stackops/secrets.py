"""Read StackOps secrets with exact selectors only."""

from __future__ import annotations

from pathlib import Path

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
    SecretSelectors,
    build_secret_candidates,
    filter_secret_candidates,
    format_secret_candidate_label,
    format_secret_selection,
)
from stackops.utils.schemas.secrets.secrets_loader import SecretsSchemaError, load_secrets_file

DEFAULT_SECRETS_PATH = Path(".stackops") / "secrets" / "secrets.json"

__all__ = [
    "DEFAULT_SECRETS_PATH",
    "SecretAmbiguousError",
    "SecretsFileError",
    "SecretLookupError",
    "SecretNotFoundError",
    "StackOpsSecretsError",
    "load_secret_value",
    "load_secret_values",
]


class StackOpsSecretsError(Exception):
    """Base exception for the Python secrets API."""


class SecretsFileError(StackOpsSecretsError, ValueError):
    """Raised when the secrets file does not match the strict schema."""


class SecretLookupError(StackOpsSecretsError, LookupError):
    """Raised when exact selectors do not resolve to one secret bundle."""


class SecretNotFoundError(SecretLookupError):
    """Raised when exact selectors match no secret bundles."""


class SecretAmbiguousError(SecretLookupError):
    """Raised when exact selectors match multiple secret bundles."""


def load_secret_value(
    key: str,
    *,
    path: str | Path | None = None,
    entry_name: str | None = None,
    secret_name: str | None = None,
    tags: tuple[str, ...] = (),
    entry_tags: tuple[str, ...] = (),
    secret_tags: tuple[str, ...] = (),
    scopes: tuple[str, ...] = (),
) -> str:
    """Return one secret value selected by exact, case-sensitive fields."""
    return load_secret_values(
        path=path,
        entry_name=entry_name,
        secret_name=secret_name,
        tags=tags,
        entry_tags=entry_tags,
        secret_tags=secret_tags,
        scopes=scopes,
        keys=(key,),
    )[key]


def load_secret_values(
    *,
    path: str | Path | None = None,
    entry_name: str | None = None,
    secret_name: str | None = None,
    tags: tuple[str, ...] = (),
    entry_tags: tuple[str, ...] = (),
    secret_tags: tuple[str, ...] = (),
    scopes: tuple[str, ...] = (),
    keys: tuple[str, ...] = (),
) -> dict[str, str]:
    """Return one `keyValues` object selected by exact, case-sensitive fields."""
    selectors = SecretSelectors(
        entry_name=entry_name,
        secret_name=secret_name,
        tags=tags,
        entry_tags=entry_tags,
        secret_tags=secret_tags,
        scopes=scopes,
        keys=keys,
    )
    if not selectors.has_any():
        raise SecretLookupError("Pass at least one exact selector.")

    try:
        candidates = build_secret_candidates(load_secrets_file(_resolve_path(path)))
    except SecretsSchemaError as exc:
        raise SecretsFileError(str(exc)) from exc

    matches = filter_secret_candidates(candidates=candidates, selectors=selectors)
    if len(matches) == 1:
        return dict(matches[0].key_values)

    selection = format_secret_selection(selectors)
    if not matches:
        raise SecretNotFoundError(f"No keyValues entry matched exact selector: {selection}")

    labels = "; ".join(format_secret_candidate_label(candidate) for candidate in matches)
    raise SecretAmbiguousError(f"Exact selector matched {len(matches)} keyValues entries: {selection}: {labels}")


def _resolve_path(path: str | Path | None) -> Path:
    if path is None:
        return Path.cwd() / DEFAULT_SECRETS_PATH

    expanded_path = Path(path).expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return Path.cwd() / expanded_path
