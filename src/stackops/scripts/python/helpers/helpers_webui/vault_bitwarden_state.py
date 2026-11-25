import json
import shutil
from typing import Literal, TypedDict, cast

from stackops.scripts.python.helpers.helpers_devops import vault as bitwarden
from stackops.secrets.paths import SECRETS_DOFILE
from stackops.secrets.search import SecretsFileError, search_logins
from stackops.utils.io import GpgCommandError, decrypt_bytes_asymmetric

# `missing` is this module's own word for a machine without the program; the others are what `bw status` says, and `unknown` is an answer
# that could not be read.
type BitwardenStatus = Literal["missing", "unauthenticated", "locked", "unlocked", "unknown"]
SPOKEN_STATUSES: dict[object, BitwardenStatus] = {"unauthenticated": "unauthenticated", "locked": "locked", "unlocked": "unlocked"}


# What can be told without running the program or opening the cache: whether `bw` is installed, and the file the commands keep on this machine.
class BitwardenPlace(TypedDict):
    installed: bool
    program: str
    cache_path: str
    cache_exists: bool
    cache_bytes: int
    cache_modified: float


# One set of Bitwarden API credentials kept in the StackOps vault, by its labels. `current` marks the account `bw` is signed in to, and `gap`
# says why Unlock could not use the set, or is empty.
class BitwardenKeySet(TypedDict):
    account: str
    email: str
    description: str
    current: bool
    gap: str


# `cache_opened` is false when a cache file is there and this machine's GPG key could not open it, which leaves the saved session unread.
class BitwardenState(TypedDict):
    status: BitwardenStatus
    account: str
    server: str
    last_sync: str
    session_saved: bool
    saved_searches: int
    cache_opened: bool
    login_name: str
    key_sets: list[BitwardenKeySet]
    key_problem: str


class BitwardenAnswer(TypedDict):
    status: BitwardenStatus
    account: str
    user_id: str
    server: str
    last_sync: str


def read_bitwarden_place() -> BitwardenPlace:
    program = shutil.which("bw")
    exists = bitwarden.CACHE_PATH.is_file()
    status = bitwarden.CACHE_PATH.stat() if exists else None
    return {
        "installed": program is not None,
        "program": program or "",
        "cache_path": str(bitwarden.CACHE_PATH),
        "cache_exists": exists,
        "cache_bytes": 0 if status is None else status.st_size,
        "cache_modified": 0.0 if status is None else status.st_mtime,
    }


# `bw status` with the saved session, read here and not through the command's own `get_vault_status`, which leaves out when the vault was last
# synced. Without the session `bw` says locked even while the saved session is good.
def ask_bitwarden(session: str | None) -> BitwardenAnswer:
    blank: BitwardenAnswer = {"status": "unknown", "account": "", "user_id": "", "server": "", "last_sync": ""}
    if shutil.which("bw") is None:
        return {**blank, "status": "missing"}
    try:
        answer: object = json.loads(bitwarden.run_command(["bw", "status"], env=bitwarden.bw_environment(session)).stdout)
    except (bitwarden.VaultExit, OSError, ValueError):
        return blank
    if not isinstance(answer, dict):
        return blank
    fields = cast(dict[str, object], answer)
    status = SPOKEN_STATUSES.get(fields.get("status"))
    if status is None:
        return blank
    return {
        "status": status,
        "account": bitwarden.get_vault_status_field(fields, "userEmail") or "",
        "user_id": bitwarden.get_vault_status_field(fields, "userId") or "",
        "server": bitwarden.get_vault_status_field(fields, "serverUrl") or "",
        "last_sync": bitwarden.get_vault_status_field(fields, "lastSync") or "",
    }


# The command's own reading of the cache answers a cache it could not open the same way as an empty one. This tells the two apart, and is
# only asked when the reading came back empty.
def _cache_opens() -> bool:
    try:
        decrypt_bytes_asymmetric(bitwarden.CACHE_PATH.read_bytes())
    except (GpgCommandError, RuntimeError, OSError):
        return False
    return True


# Opens the cache with this machine's GPG key, as every Bitwarden command does first, and asks `bw` how it stands. The session itself stays
# in this process. The API credentials are read from the user's vault file the way Unlock reads them, and only their labels are returned.
def read_bitwarden_state() -> BitwardenState:
    cache = bitwarden.load_encrypted_cache()
    session = cache.get("BW_SESSION")
    answer = ask_bitwarden(session=session)
    key_sets: list[BitwardenKeySet] = []
    key_problem = ""
    if SECRETS_DOFILE.is_file():
        try:
            logins = search_logins(path=SECRETS_DOFILE, login_name=bitwarden.DEFAULT_BITWARDEN_LOGIN_NAME, keys=bitwarden.BITWARDEN_SECRET_KEYS)
        except SecretsFileError:
            logins = []
            key_problem = "Your vault file cannot be read, so the API key in it cannot be used."
        for login in logins:
            values = login["secrets"][0]["keyValues"]
            client_id = str(values.get("BW_CLIENTID") or "")
            empty = [key for key in bitwarden.BITWARDEN_SECRET_KEYS if not values.get(key)]
            gap = (
                f"""It has no value for {", ".join(empty)}."""
                if empty
                else "Its client ID is not a personal API key. A personal one starts with user."
                if not client_id.startswith(bitwarden.BITWARDEN_CLIENT_ID_USER_PREFIX) or client_id == bitwarden.BITWARDEN_CLIENT_ID_USER_PREFIX
                else ""
            )
            key_sets.append({
                "account": login.get("accountName", ""),
                "email": login.get("email", ""),
                "description": login.get("description", ""),
                "current": answer["user_id"] != "" and client_id == f"""{bitwarden.BITWARDEN_CLIENT_ID_USER_PREFIX}{answer["user_id"]}""",
                "gap": gap,
            })
    return {
        "status": answer["status"],
        "account": answer["account"],
        "server": answer["server"],
        "last_sync": answer["last_sync"],
        "session_saved": bool(session),
        "saved_searches": sum(1 for key in cache if key.startswith("search::")),
        "cache_opened": len(cache) > 0 or not bitwarden.CACHE_PATH.is_file() or _cache_opens(),
        "login_name": bitwarden.DEFAULT_BITWARDEN_LOGIN_NAME,
        "key_sets": key_sets,
        "key_problem": key_problem,
    }
