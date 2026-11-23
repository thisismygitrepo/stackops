import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

import stackops.secrets.assets as secrets_assets
from stackops.scripts.python.helpers.helpers_webui.vault_form import VaultProblem, login_from_form
from stackops.scripts.python.helpers.helpers_webui.vault_views import vault_sources
from stackops.secrets.constants import SECRETS_FILE_VERSION
from stackops.secrets.loader import SecretsSchemaError, load_secrets_file, parse_secret_login
from stackops.secrets.models import Login, SecretsFile
from stackops.secrets.writer import create_secrets_file, replace_secrets_file
from stackops.utils.managed_files import ensure_managed_schema, get_managed_file_spec

MOVED_ON = "This vault file changed on disk after the page read it. The list is being read again, so try once more."
GONE = "That login is no longer in the vault."


class VaultLoginView(TypedDict):
    login: Login


class VaultSaved(TypedDict):
    index: int


# A vault file opened to work on one login: `payload` is the file as written, which is what gets changed and saved, so the other entries stay
# exactly as they are. `logins` are the same entries as the loader reads them. Both are empty for a file that does not exist yet.
@dataclass(frozen=True)
class OpenedVault:
    path: Path
    payload: dict[str, object] | None
    logins: list[Login]


# `version` is what the page was shown, and is checked for anything that names a login by its place in the file: a place only means the same
# login while the file is the same. None skips the check, for adding a login, which is right whatever the file holds by now.
def _open_vault(base_directory: str, source: str, version: str | None) -> OpenedVault | VaultProblem:
    try:
        path = dict(vault_sources(base_directory)).get(source)
    except ValueError as error:
        return VaultProblem(status=400, message=str(error))
    if path is None:
        return VaultProblem(status=404, message=f"""There is no vault file called {source} for this folder.""")
    content = path.read_bytes() if path.is_file() else None
    if version is not None and version != ("" if content is None else hashlib.sha256(content).hexdigest()):
        return VaultProblem(status=409, message=MOVED_ON)
    if content is None:
        return OpenedVault(path=path, payload=None, logins=[])
    try:
        logins = load_secrets_file(path)["entries"]
    except SecretsSchemaError as error:
        return VaultProblem(status=422, message=str(error))
    return OpenedVault(path=path, payload=cast(dict[str, object], json.loads(content)), logins=logins)


# One login with its values as they are, for the page to show or copy a value the person asked for.
def read_vault_login(base_directory: str, source: str, index: str, version: str) -> VaultLoginView | VaultProblem:
    opened = _open_vault(base_directory=base_directory, source=source, version=version)
    match opened:
        case VaultProblem():
            return opened
        case OpenedVault():
            if not index.isdecimal() or int(index) >= len(opened.logins):
                return VaultProblem(status=404, message=GONE)
            return {"login": opened.logins[int(index)]}


# Adds a login when `index` is null and replaces the one at `index` otherwise. A file that does not exist yet is created with its schema beside it.
def save_vault_login(body: object) -> VaultSaved | VaultProblem:
    payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
    base_directory, source, version, index = payload.get("base"), payload.get("source"), payload.get("version"), payload.get("index")
    if not isinstance(base_directory, str) or not isinstance(source, str):
        return VaultProblem(status=400, message="`base` and `source` must be text.")
    if index is None:
        opened = _open_vault(base_directory=base_directory, source=source, version=None)
    elif isinstance(index, int) and not isinstance(index, bool) and isinstance(version, str):
        opened = _open_vault(base_directory=base_directory, source=source, version=version)
    else:
        return VaultProblem(status=400, message="`index` must be null, or a whole number sent with the `version` of the file it was read from.")
    match opened:
        case VaultProblem():
            return opened
        case OpenedVault():
            if index is not None and not 0 <= index < len(opened.logins):
                return VaultProblem(status=404, message=GONE)
    entry = login_from_form(form=payload.get("login"), original=None if index is None else opened.logins[index])
    match entry:
        case VaultProblem():
            return entry
        case dict():
            try:
                login = parse_secret_login(entry=entry, entry_index=len(opened.logins) if index is None else index)
            except SecretsSchemaError as error:
                return VaultProblem(status=422, message=str(error))
    if opened.payload is None:
        create_secrets_file(
            secrets_path=opened.path,
            secrets_file={"$schema": f"""./{secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE}""", "version": SECRETS_FILE_VERSION, "entries": [login]},
        )
        ensure_managed_schema(spec=get_managed_file_spec("secrets"), data_path=opened.path)
        return {"index": 0}
    entries = cast(list[object], opened.payload["entries"])
    if index is None:
        entries.append(login)
    else:
        entries[index] = login
    replace_secrets_file(secrets_path=opened.path, secrets_file=cast(SecretsFile, opened.payload))
    return {"index": len(entries) - 1 if index is None else index}


# A vault file must hold at least one login, so removing the last one removes the file; adding a login later creates it again.
def delete_vault_login(base_directory: str, source: str, index: str, version: str) -> VaultProblem | None:
    opened = _open_vault(base_directory=base_directory, source=source, version=version)
    match opened:
        case VaultProblem():
            return opened
        case OpenedVault():
            if opened.payload is None or not index.isdecimal() or int(index) >= len(opened.logins):
                return VaultProblem(status=404, message=GONE)
            entries = cast(list[object], opened.payload["entries"])
            del entries[int(index)]
            if len(entries) == 0:
                opened.path.unlink()
            else:
                replace_secrets_file(secrets_path=opened.path, secrets_file=cast(SecretsFile, opened.payload))
            return None
