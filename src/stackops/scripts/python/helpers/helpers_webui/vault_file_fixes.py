from pathlib import Path
from typing import Literal, TypedDict, cast

from stackops.scripts.python.helpers.helpers_webui.vault_file_problem import VaultFileFinding, explain_vault_problem
from stackops.scripts.python.helpers.helpers_webui.vault_form import VaultProblem
from stackops.scripts.python.helpers.helpers_webui.vault_views import vault_sources
from stackops.secrets.writer import PRIVATE_SECRETS_FILE_MODE
from stackops.utils.managed_file_operations import initialize_managed_file, validate_managed_file
from stackops.utils.managed_files import ensure_managed_schema, get_managed_file_spec

NOT_THERE = "That vault file is not there any more. The page is reading the files again."


# What `devops vault validate` makes of a file: valid, invalid with what is wrong, or unchecked when the check itself could not run.
class VaultCheckView(TypedDict):
    verdict: Literal["valid", "invalid", "unchecked"]
    finding: VaultFileFinding | None
    trouble: str


class VaultFixed(TypedDict):
    path: str


# The file the page names by `source` (user, workspace, workspace:<member>) for the folder it works in.
def resolve_vault_file(base_directory: str, source: str) -> Path | VaultProblem:
    try:
        path = dict(vault_sources(base_directory)).get(source)
    except ValueError as error:
        return VaultProblem(status=400, message=str(error))
    return VaultProblem(status=404, message=f"""There is no vault file called {source} for this folder.""") if path is None else path


def _named_file(body: object) -> Path | VaultProblem:
    payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
    base_directory, source = payload.get("base"), payload.get("source")
    if not isinstance(base_directory, str) or not isinstance(source, str):
        return VaultProblem(status=400, message="`base` and `source` must be text.")
    return resolve_vault_file(base_directory=base_directory, source=source)


# The command's full check: the file against its schema, in a process of its own, and then the vault's own reading of it. It takes a second or
# more, and needs the jsonschema package, which uv fetches the first time.
def check_vault_file(base_directory: str, source: str) -> VaultCheckView | VaultProblem:
    path = resolve_vault_file(base_directory=base_directory, source=source)
    match path:
        case VaultProblem():
            return path
        case Path():
            if not path.is_file():
                return VaultProblem(status=404, message=NOT_THERE)
    try:
        validate_managed_file(kind="secrets", data_path=path)
    except ValueError as error:
        # The checking process can print notes of its own first (uv says what it fetched); its verdict is the last line.
        lines = str(error).strip().splitlines()
        said = lines[-1] if lines else "The check stopped without saying why."
        if said.startswith(("Invalid secret", "Invalid JSON", "Secrets file")):
            return {"verdict": "invalid", "finding": explain_vault_problem(message=said, path=path), "trouble": ""}
        return {"verdict": "unchecked", "finding": None, "trouble": said}
    except OSError as error:
        return {"verdict": "unchecked", "finding": None, "trouble": str(error)}
    return {"verdict": "valid", "finding": None, "trouble": ""}


# What `devops vault init` does for a file that is missing: the file, started from the example, and its schema beside it.
def create_vault_file(body: object) -> VaultFixed | VaultProblem:
    path = _named_file(body)
    match path:
        case VaultProblem():
            return path
        case Path():
            if path.exists():
                return VaultProblem(status=409, message="A vault file is already there, so nothing was created.")
    try:
        initialize_managed_file(spec=get_managed_file_spec("secrets"), data_path=path)
    except (OSError, ValueError) as error:
        return VaultProblem(status=422, message=f"""The vault file could not be created. {error}""")
    return {"path": str(path)}


def refresh_vault_schema(body: object) -> VaultFixed | VaultProblem:
    path = _named_file(body)
    match path:
        case VaultProblem():
            return path
        case Path():
            if not path.is_file():
                return VaultProblem(status=404, message=NOT_THERE)
    try:
        ensure_managed_schema(spec=get_managed_file_spec("secrets"), data_path=path)
    except OSError as error:
        return VaultProblem(status=422, message=f"""The schema file could not be written. {error}""")
    return {"path": str(path)}


def protect_vault_file(body: object) -> VaultFixed | VaultProblem:
    path = _named_file(body)
    match path:
        case VaultProblem():
            return path
        case Path():
            if not path.is_file():
                return VaultProblem(status=404, message=NOT_THERE)
    try:
        path.chmod(PRIVATE_SECRETS_FILE_MODE)
    except OSError as error:
        return VaultProblem(status=422, message=f"""The file's permissions could not be changed. {error}""")
    return {"path": str(path)}
