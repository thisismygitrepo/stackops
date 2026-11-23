import hashlib
from pathlib import Path
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_webui.constants import VAULT_MASK, VAULT_PARTIAL_EDGE_LIMIT, VAULT_PARTIAL_EDGE_SHARE, VaultReveal
from stackops.scripts.python.helpers.helpers_webui.vault_form import VaultProblem
from stackops.secrets.loader import SecretsSchemaError, load_secrets_file
from stackops.secrets.paths import SECRETS_DOFILE
from stackops.secrets.search import render_secret_value
from stackops.utils.repos.stackops_paths import workspace_stackops_paths


# One value of a secret as the page lists it. `text` is None while values are hidden, so a hidden value never leaves this machine's memory.
class VaultValueView(TypedDict):
    key: str
    text: str | None
    json: bool


# `version` is the hash of the file as it was read, and empty for a file that does not exist yet. `problem` says why a file could not be read.
# Each login is the file's own entry with its place in the file as `index`, and each secret's `keyValues` replaced by `values`.
class VaultSourceView(TypedDict):
    name: str
    path: str
    exists: bool
    version: str
    problem: str
    logins: list[dict[str, object]]


class VaultView(TypedDict):
    sources: list[VaultSourceView]


# The files the CLI reads from `base_directory` with `--source all`: the project's own, one per member of a workspace, then the user's.
def vault_sources(base_directory: str) -> list[tuple[str, Path]]:
    return [*workspace_stackops_paths(current_dir=Path(base_directory), path_kind="secrets_json"), ("user", SECRETS_DOFILE)]


def read_vault(base_directory: str, reveal: str) -> VaultView | VaultProblem:
    match reveal:
        case "hidden" | "partial" | "full":
            try:
                sources = vault_sources(base_directory)
            except ValueError as error:
                return VaultProblem(status=400, message=str(error))
            return {"sources": [_source_view(name=name, path=path, reveal=reveal) for name, path in sources]}
        case _:
            return VaultProblem(status=400, message="`reveal` must be hidden, partial or full.")


def _source_view(name: str, path: Path, reveal: VaultReveal) -> VaultSourceView:
    if not path.is_file():
        return {"name": name, "path": str(path), "exists": False, "version": "", "problem": "", "logins": []}
    version = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        entries = load_secrets_file(path)["entries"]
    except SecretsSchemaError as error:
        return {"name": name, "path": str(path), "exists": True, "version": version, "problem": str(error), "logins": []}
    logins: list[dict[str, object]] = [
        {
            **login,
            "index": index,
            "secrets": [
                {
                    **{field: content for field, content in secret.items() if field != "keyValues"},
                    "values": [_value_view(key=key, value=value, reveal=reveal) for key, value in secret["keyValues"].items()],
                }
                for secret in login["secrets"]
            ],
        }
        for index, login in enumerate(entries)
    ]
    return {"name": name, "path": str(path), "exists": True, "version": version, "problem": "", "logins": logins}


def _value_view(key: str, value: object, reveal: VaultReveal) -> VaultValueView:
    text = render_secret_value(value)
    edge = min(VAULT_PARTIAL_EDGE_LIMIT, len(text) // VAULT_PARTIAL_EDGE_SHARE)
    match reveal:
        case "hidden":
            shown = None
        case "partial":
            shown = f"""{text[:edge]}{VAULT_MASK}{text[len(text) - edge:]}"""
        case "full":
            shown = text
    return {"key": key, "text": shown, "json": not isinstance(value, str)}
