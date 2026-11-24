import hashlib
from pathlib import Path
from typing import TypedDict, cast

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_actions import subset_secrets_file
from stackops.scripts.python.helpers.helpers_webui.vault_file_constants import VaultCopyConflict, VaultCopyTargetState
from stackops.scripts.python.helpers.helpers_webui.vault_file_fixes import resolve_vault_file
from stackops.scripts.python.helpers.helpers_webui.vault_form import VaultProblem
from stackops.scripts.python.helpers.helpers_webui.vault_store import MOVED_ON
from stackops.secrets.loader import SecretsSchemaError, load_secrets_file


# The place a copy is to be written to, as it stands now. `logins` is how many a vault file there already holds, and `same_version` says its
# version is the one of the file being copied from, which adding to it needs.
class VaultCopyTarget(TypedDict):
    path: str
    state: VaultCopyTargetState
    logins: int
    same_version: bool


class VaultCopied(TypedDict):
    path: str
    copied: int
    secrets: int
    holds: int


# A path that is not absolute is taken from the folder the page works in, not from wherever the server was started.
def describe_copy_target(base_directory: str, source: str, text: str) -> VaultCopyTarget | VaultProblem:
    source_path = resolve_vault_file(base_directory=base_directory, source=source)
    match source_path:
        case VaultProblem():
            return source_path
        case Path():
            if text.strip() == "":
                return VaultProblem(status=400, message="Say where the copy goes.")
    typed = Path(text.strip()).expanduser()
    path = typed if typed.is_absolute() else Path(base_directory) / typed
    if path.resolve(strict=False) == source_path.resolve(strict=False):
        return {"path": str(path), "state": "same", "logins": 0, "same_version": False}
    if path.is_dir():
        return {"path": str(path), "state": "folder", "logins": 0, "same_version": False}
    if not path.exists():
        return {"path": str(path), "state": "free", "logins": 0, "same_version": False}
    try:
        there = load_secrets_file(path)
    except (SecretsSchemaError, OSError, UnicodeDecodeError):
        return {"path": str(path), "state": "other", "logins": 0, "same_version": False}
    try:
        same_version = load_secrets_file(source_path)["version"] == there["version"]
    except SecretsSchemaError:
        same_version = False
    return {"path": str(path), "state": "vault", "logins": len(there["entries"]), "same_version": same_version}


# The chosen logins, named by their places in the file as the page was shown it, written with `devops vault subset`'s own code. `conflict` only
# matters when a file is already there: `throw-error` then refuses, `overwrite` replaces it and `append` adds to it.
def copy_vault_logins(body: object) -> VaultCopied | VaultProblem:
    payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
    base_directory, source, version, text, conflict = payload.get("base"), payload.get("source"), payload.get("version"), payload.get("path"), payload.get("conflict")
    indices_raw = payload.get("indices")
    if not isinstance(base_directory, str) or not isinstance(source, str) or not isinstance(version, str) or not isinstance(text, str):
        return VaultProblem(status=400, message="`base`, `source`, `version` and `path` must be text.")
    if not isinstance(indices_raw, list) or len(cast(list[object], indices_raw)) == 0:
        return VaultProblem(status=400, message="Choose at least one login to copy.")
    indices = [index for index in cast(list[object], indices_raw) if isinstance(index, int) and not isinstance(index, bool)]
    if len(indices) != len(cast(list[object], indices_raw)):
        return VaultProblem(status=400, message="`indices` must be whole numbers.")
    source_path = resolve_vault_file(base_directory=base_directory, source=source)
    match source_path:
        case VaultProblem():
            return source_path
        case Path():
            pass
    target = describe_copy_target(base_directory=base_directory, source=source, text=text)
    match target:
        case VaultProblem():
            return target
        case _:
            pass
    if not source_path.is_file() or hashlib.sha256(source_path.read_bytes()).hexdigest() != version:
        return VaultProblem(status=409, message=MOVED_ON)
    on_conflict: VaultCopyConflict
    match target["state"], conflict:
        case "same", _:
            return VaultProblem(status=422, message="The copy cannot go to the file it is taken from.")
        case "folder", _:
            return VaultProblem(status=422, message="That is a folder. Give the copy a file name inside it.")
        case "free", _:
            on_conflict = "throw-error"
        case _, "overwrite":
            on_conflict = "overwrite"
        case "vault", "append":
            if not target["same_version"]:
                return VaultProblem(status=422, message="The file there was written for another version of the vault, so nothing can be added to it. Replace it, or choose another place.")
            on_conflict = "append"
        case "other", "append":
            return VaultProblem(status=422, message="The file there is not a vault file, so nothing can be added to it. Replace it, or choose another place.")
        case _:
            return VaultProblem(status=409, message="A file is already there. Choose whether to add to it or replace it.")
    try:
        receipt = subset_secrets_file(
            source_path=source_path, output_path=Path(target["path"]), on_conflict=on_conflict, preview_secrets=False,
            names=[], entry_indices=indices, all_matches=False, dry_run=False,
        )
    except typer.BadParameter as error:
        return VaultProblem(status=422, message=f"""The copy was not made. {error.message}""")
    except OSError as error:
        return VaultProblem(status=422, message=f"""The copy was not made. {error}""")
    except typer.Exit:
        return VaultProblem(status=422, message="The copy was not made. Something about the files changed in between, so look at the place again.")
    return {"path": receipt["path"], "copied": receipt["selected_entries"], "secrets": receipt["secret_bundles"], "holds": receipt["output_entries"]}
