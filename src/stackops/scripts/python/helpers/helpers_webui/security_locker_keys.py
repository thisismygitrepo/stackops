import re
import shutil
import subprocess
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_webui.security_constants import GPG_LIST_TIMEOUT_SECONDS

# Whether GPG would encrypt for a key without asking anything. It refuses, unattended, a key it has not been told to trust.
type KeyState = Literal["usable", "expired", "revoked", "disabled", "cannot_encrypt", "untrusted"]
TRUSTED_VALIDITIES: frozenset[str] = frozenset({"u", "f"})


# One key GPG holds on this machine. `mine` says its private half is here too, so files encrypted for it can be opened here.
# `ids` holds the IDs of the key and of its parts; an encrypted file names the part it was made for.
class KeyView(TypedDict):
    fingerprint: str
    id: str
    name: str
    email: str
    created: float | None
    expires: float | None
    state: KeyState
    mine: bool
    ids: list[str]


# `own` is the fingerprint of the key a file is encrypted for when none is picked: the first key whose private half is here. GPG encrypts for
# that one without asking even when it has not been told to trust it; a key that is named has to be trusted.
# Not exact by design: a default key named in GPG's own settings wins over it, and that file is not read here.
class LockerState(TypedDict):
    gpg: bool
    version: str
    keys: list[KeyView]
    own: str


def _gpg(arguments: list[str]) -> str:
    try:
        completed = subprocess.run(["gpg", "--batch", *arguments], capture_output=True, text=True, check=False, timeout=GPG_LIST_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout if completed.returncode == 0 else ""


def _stamp(text: str) -> float | None:
    return float(text) if text.isdigit() else None


def _key_state(validity: str, capabilities: str) -> KeyState:
    match validity:
        case "e":
            return "expired"
        case "r":
            return "revoked"
        case "d":
            return "disabled"
        case _:
            pass
    if "D" in capabilities:
        return "disabled"
    if "E" not in capabilities:
        return "cannot_encrypt"
    return "usable" if validity in TRUSTED_VALIDITIES else "untrusted"


# GPG's listing for programs: one record per line, fields between colons. A key starts at "pub", its parts are "sub", its names "uid".
def _parse_keys(listing: str, secret_ids: frozenset[str]) -> list[KeyView]:
    keys: list[KeyView] = []
    for line in listing.splitlines():
        fields = line.split(":")
        record = fields[0]
        if record == "pub" and len(fields) > 11:
            keys.append(
                {
                    "fingerprint": "", "id": fields[4], "name": "", "email": "", "created": _stamp(fields[5]), "expires": _stamp(fields[6]),
                    "state": _key_state(validity=fields[1], capabilities=fields[11]), "mine": fields[4] in secret_ids, "ids": [fields[4]],
                }
            )
        elif len(keys) == 0 or len(fields) < 10:
            continue
        elif record == "fpr" and keys[-1]["fingerprint"] == "":
            keys[-1]["fingerprint"] = fields[9]
        elif record == "sub":
            keys[-1]["ids"].append(fields[4])
        elif record == "uid" and keys[-1]["name"] == "" and keys[-1]["email"] == "":
            shown = re.sub(r"\\x([0-9a-fA-F]{2})", lambda escaped: chr(int(escaped.group(1), 16)), fields[9])
            named = re.fullmatch(r"(.*?)\s*<([^<>]*)>", shown)
            keys[-1]["name"] = shown if named is None else named.group(1)
            keys[-1]["email"] = "" if named is None else named.group(2)
    return keys


def read_secret_key_ids() -> frozenset[str]:
    records = [line.split(":") for line in _gpg(["--with-colons", "--list-secret-keys"]).splitlines()]
    return frozenset(fields[4] for fields in records if fields[0] in ("sec", "ssb") and len(fields) > 4)


def read_locker_state() -> LockerState:
    if shutil.which("gpg") is None:
        return {"gpg": False, "version": "", "keys": [], "own": ""}
    version_line = _gpg(["--version"]).splitlines()[:1]
    version = re.search(r"\d+(\.\d+)+", version_line[0]) if version_line else None
    secret_ids = read_secret_key_ids()
    keys = _parse_keys(listing=_gpg(["--with-colons", "--list-keys"]), secret_ids=secret_ids)
    own = next((key["fingerprint"] for key in keys if key["mine"] and key["state"] in ("usable", "untrusted")), "")
    return {"gpg": True, "version": "" if version is None else version.group(0), "keys": keys, "own": own}
