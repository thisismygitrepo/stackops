import base64
import getpass
import hashlib
import os
import platform
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_posix import add_ssh_keys_posix
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_add_key_windows import add_ssh_key_windows
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_keys import (
    PRIVATE_KEY_MARKERS,
    SUPPORTED_KEY_TYPES,
    PublicKeyRecord,
    parse_public_key_records,
    read_public_key_file,
)
from stackops.scripts.python.helpers.helpers_webui.network_constants import SSH_CERTIFICATE_SUFFIX, SSH_FINGERPRINT_PREFIX, SSH_KEY_TEXT_LIMIT

KEY_KINDS: dict[str, str] = {
    "ssh-ed25519": "Ed25519",
    "ssh-rsa": "RSA",
    "ecdsa-sha2-nistp256": "ECDSA 256",
    "ecdsa-sha2-nistp384": "ECDSA 384",
    "ecdsa-sha2-nistp521": "ECDSA 521",
    "sk-ssh-ed25519@openssh.com": "Security key (Ed25519)",
    "sk-ecdsa-sha2-nistp256@openssh.com": "Security key (ECDSA)",
}


@dataclass(frozen=True, slots=True)
class KeyProblem:
    status: int
    message: str


# What the page is told about a public key. The key itself is not sent: its fingerprint names it.
class KeyView(TypedDict):
    name: str
    type: str
    kind: str
    bits: int
    fingerprint: str
    allowed: bool


# One line of the file that says who may sign in. `limits` are the restrictions written in front of the key, such as a single command or a
# source address. A line that is not a usable key keeps `problem` and has no fingerprint.
class AllowedKey(TypedDict):
    file: str
    line: int
    name: str
    type: str
    kind: str
    bits: int
    fingerprint: str
    limits: list[str]
    problem: str


class KeyFile(TypedDict):
    path: str
    name: str
    keys: list[KeyView]
    problem: str


class KeysOverview(TypedDict):
    user: str
    files: list[str]
    keys: list[AllowedKey]
    problem: str
    candidates: list[KeyFile]


class AddResult(TypedDict):
    file: str
    added: int
    already: int


def describe_key(key_type: str, encoded_key: str) -> tuple[str, int]:
    blob = base64.b64decode(encoded_key + "=" * (-len(encoded_key) % 4))
    fingerprint = SSH_FINGERPRINT_PREFIX + base64.b64encode(hashlib.sha256(blob).digest()).decode("ascii").rstrip("=")
    if key_type != "ssh-rsa":
        return fingerprint, 256 if "25519" in key_type else int(key_type.rsplit("nistp", maxsplit=1)[-1].split("@", maxsplit=1)[0])
    # An RSA key is its name, its exponent and its modulus, each behind a four-byte length. The modulus says how strong the key is.
    offset = 0
    field = b""
    for _ in range(3):
        length = int.from_bytes(blob[offset : offset + 4], byteorder="big")
        field = blob[offset + 4 : offset + 4 + length]
        offset += 4 + length
    return fingerprint, int.from_bytes(field, byteorder="big").bit_length()


def view_of(record: PublicKeyRecord, allowed: frozenset[str]) -> KeyView:
    parts = record.text.split(maxsplit=2)
    fingerprint, bits = describe_key(key_type=parts[0], encoded_key=parts[1])
    return {"name": parts[2] if len(parts) == 3 else "", "type": parts[0], "kind": KEY_KINDS[parts[0]], "bits": bits, "fingerprint": fingerprint, "allowed": fingerprint in allowed}


# The files OpenSSH reads on this machine for the person the server runs as: the one in their home folder, and on Windows also the one all
# administrators share. The CLI's add command writes to one of the two (`ssh_add_key_windows.py`).
def authorization_files() -> list[Path]:
    files = [Path.home().joinpath(".ssh", "authorized_keys")]
    program_data = os.environ.get("PROGRAMDATA", "")
    if platform.system() == "Windows" and program_data != "":
        files.append(Path(program_data).joinpath("ssh", "administrators_authorized_keys"))
    return files


# The restrictions written in front of a key are one word, split at the commas that are not inside quotes. Only which ones are set is shown,
# never their values: a value can be a command or an address.
def limit_names(options: str) -> list[str]:
    names: list[str] = []
    current = ""
    quoted = False
    for character in options.strip():
        if character == '"':
            quoted = not quoted
        if character == "," and not quoted:
            names.append(current)
            current = ""
        else:
            current += character
    names.append(current)
    return sorted({name.split("=", maxsplit=1)[0].strip() for name in names if name.strip() != ""})


def read_allowed_line(file: Path, number: int, line: str) -> AllowedKey:
    entry: AllowedKey = {"file": str(file), "line": number, "name": "", "type": "", "kind": "", "bits": 0, "fingerprint": "", "limits": [], "problem": ""}
    try:
        tokens = shlex.split(line, comments=False, posix=True)
    except ValueError:
        return {**entry, "problem": "This line has a quote that is never closed."}
    index = next((position for position, token in enumerate(tokens) if token in SUPPORTED_KEY_TYPES), None)
    if index is None or index + 1 >= len(tokens):
        return {**entry, "problem": "This line is not a public key of a kind StackOps accepts."}
    try:
        parse_public_key_records(value=f"{tokens[index]} {tokens[index + 1]}", source="This line")
    except ValueError:
        return {**entry, "type": tokens[index], "name": " ".join(tokens[index + 2 :]), "problem": "The key on this line is damaged, so nobody can sign in with it."}
    fingerprint, bits = describe_key(key_type=tokens[index], encoded_key=tokens[index + 1])
    limits = limit_names(options=line.split(tokens[index], maxsplit=1)[0]) if index > 0 else []
    return {**entry, "name": " ".join(tokens[index + 2 :]), "type": tokens[index], "kind": KEY_KINDS[tokens[index]], "bits": bits, "fingerprint": fingerprint, "limits": limits}


def read_allowed_keys() -> tuple[list[AllowedKey], str]:
    keys: list[AllowedKey] = []
    for file in authorization_files():
        try:
            text = file.read_text(encoding="utf-8")
        except FileNotFoundError:
            continue
        except (OSError, UnicodeDecodeError) as error:
            return keys, f"""{file} could not be read: {error}"""
        for number, line in enumerate(text.splitlines(), start=1):
            if line.strip() != "" and not line.lstrip().startswith("#"):
                keys.append(read_allowed_line(file=file, number=number, line=line.strip()))
    return keys, ""


# This machine's own public keys, the ones in ~/.ssh: offered because allowing one lets this machine sign in to itself and to any machine
# that shares its home folder. Private keys are never opened: only files that end in .pub are read.
def read_candidates(allowed: frozenset[str]) -> list[KeyFile]:
    candidates: list[KeyFile] = []
    for path in sorted(Path.home().joinpath(".ssh").glob("*.pub")):
        if not path.is_file() or path.name.endswith(SSH_CERTIFICATE_SUFFIX):
            continue
        try:
            keys = [view_of(record=record, allowed=allowed) for record in read_public_key_file(path=path)]
        except (OSError, ValueError):
            candidates.append({"path": str(path), "name": path.name, "keys": [], "problem": "This file does not hold a public key StackOps accepts."})
            continue
        candidates.append({"path": str(path), "name": path.name, "keys": keys, "problem": ""})
    return candidates


def read_keys_overview() -> KeysOverview:
    keys, problem = read_allowed_keys()
    allowed = frozenset(key["fingerprint"] for key in keys if key["fingerprint"] != "")
    return {"user": getpass.getuser(), "files": [str(file) for file in authorization_files()], "keys": keys, "problem": problem, "candidates": read_candidates(allowed=allowed)}


# The keys a request names, checked the way the CLI's add command checks them: pasted text, or a file on this machine.
def read_offered_keys(body: object) -> list[PublicKeyRecord] | KeyProblem:
    payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
    source = payload.get("source")
    text = payload.get("text")
    path = payload.get("path")
    try:
        if source == "pasted" and isinstance(text, str):
            if len(text) > SSH_KEY_TEXT_LIMIT:
                return KeyProblem(status=422, message="That is far more text than a few public keys.")
            if any(marker in text.upper() for marker in PRIVATE_KEY_MARKERS):
                return KeyProblem(status=422, message="That is a private key, and it must never leave the machine it belongs to. Paste the public one: a single line that starts with ssh-ed25519 or ssh-rsa.")
            if text.strip() == "":
                return KeyProblem(status=422, message="Paste a public key first.")
            return parse_public_key_records(value=text, source="What you pasted")
        if source == "file" and isinstance(path, str) and path.strip() != "":
            return read_public_key_file(path=Path(path.strip()).expanduser().absolute())
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return KeyProblem(status=422, message=str(error))
    return KeyProblem(status=400, message="Send `source` as pasted with `text`, or as file with `path`.")


def check_offered_keys(body: object) -> list[KeyView] | KeyProblem:
    records = read_offered_keys(body)
    if isinstance(records, KeyProblem):
        return records
    keys, _problem = read_allowed_keys()
    allowed = frozenset(key["fingerprint"] for key in keys if key["fingerprint"] != "")
    return [view_of(record=record, allowed=allowed) for record in records]


# Adds through the CLI's own writers, which make the folder and the file with the rights OpenSSH insists on and never write a key twice.
# A key that is already allowed under another name is left out here, where the CLI would add it a second time.
def add_offered_keys(body: object) -> AddResult | KeyProblem:
    records = read_offered_keys(body)
    if isinstance(records, KeyProblem):
        return records
    keys, _problem = read_allowed_keys()
    allowed = frozenset(key["fingerprint"] for key in keys if key["fingerprint"] != "")
    fresh = [record for record in records if not view_of(record=record, allowed=allowed)["allowed"]]
    if len(fresh) == 0:
        return {"file": str(authorization_files()[0]), "added": 0, "already": len(records)}
    try:
        file, added = add_ssh_key_windows(records=fresh) if platform.system() == "Windows" else add_ssh_keys_posix(records=fresh)
    except (OSError, RuntimeError, ValueError) as error:
        return KeyProblem(status=500, message=f"""The key was not added: {error}""")
    return {"file": str(file), "added": added, "already": len(records) - added}
