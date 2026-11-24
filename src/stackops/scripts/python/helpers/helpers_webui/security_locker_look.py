import base64
import binascii
from pathlib import Path
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt import (
    FOLDER_ARCHIVE_SUFFIXES,
    FolderArchiveFormat,
    _default_encrypted_output,  # pyright: ignore[reportPrivateUsage]
    _match_archive_suffix,  # pyright: ignore[reportPrivateUsage]
)
from stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt_output import validate_output
from stackops.scripts.python.helpers.helpers_webui.security_constants import ENCRYPTED_SNIFF_BYTES, FOLDER_MEASURE_LIMIT
from stackops.scripts.python.helpers.helpers_webui.security_paths import PathMeasure, measure_path

type LockerMode = Literal["encrypt", "decrypt"]
# How a file was encrypted, read from its first bytes: with a password, for one or more keys, in a way that cannot be told, or not at all.
type LockMethod = Literal["password", "key", "unknown", "none"]
# Why the command would refuse the file or the place for its result.
type LookProblem = Literal["missing", "not_file", "not_gpg_name", "no_name", "overlap", "exists"]

ARMOR_HEADER = b"-----BEGIN PGP MESSAGE-----"
KEY_PACKET = 1
PASSWORD_PACKET = 3
DATA_PACKETS = frozenset({9, 18, 20})
COMPRESSIONS: tuple[FolderArchiveFormat, ...] = tuple(FOLDER_ARCHIVE_SUFFIXES)


# `key_ids` names the keys a file was encrypted for. `have_key` says the private half of one of them is on this machine.
class EncryptedView(TypedDict):
    method: LockMethod
    key_ids: list[str]
    have_key: bool


# What the run would make. `unpacks` is the archive ending of a folder that was packed before it was encrypted, and empty for a plain file.
class LookView(TypedDict):
    source: PathMeasure
    encrypted: EncryptedView
    output: str
    default_output: str
    unpacks: str
    problem: LookProblem | None


def _armored_body(head: bytes) -> bytes:
    lines = head.split(b"\n")[1:]
    blank = next((index for index, line in enumerate(lines) if line.strip() == b""), -1)
    body = b"".join(line.strip() for line in lines[blank + 1 :] if not line.startswith((b"=", b"-----")))
    try:
        return base64.b64decode(body[: len(body) - len(body) % 4])
    except binascii.Error:
        return b""


# The packets an OpenPGP message opens with, as (kind, content). An encrypted message starts with one packet per key or password it can be
# opened with; reading stops at the first packet of another kind, or where the bytes read run out.
def _leading_packets(data: bytes) -> list[tuple[int, bytes]]:
    packets: list[tuple[int, bytes]] = []
    offset = 0
    while offset + 1 < len(data) and data[offset] & 0x80:
        first = data[offset]
        offset += 1
        if first & 0x40:
            tag = first & 0x3F
            size = data[offset]
            if size < 192:
                length, offset = size, offset + 1
            elif size < 224 and offset + 1 < len(data):
                length, offset = ((size - 192) << 8) + data[offset + 1] + 192, offset + 2
            elif size == 255:
                length, offset = int.from_bytes(data[offset + 1 : offset + 5], "big"), offset + 5
            else:
                length = len(data)
        else:
            tag = (first >> 2) & 0x0F
            width = (1, 2, 4, 0)[first & 0x03]
            length = int.from_bytes(data[offset : offset + width], "big") if width else len(data)
            offset += width
        packets.append((tag, data[offset : offset + length]))
        offset += length
        if tag not in (KEY_PACKET, PASSWORD_PACKET):
            break
    return packets


def sniff_encrypted(path: Path, secret_ids: frozenset[str]) -> EncryptedView:
    try:
        with path.open("rb") as opened:
            head = opened.read(ENCRYPTED_SNIFF_BYTES)
    except OSError:
        head = b""
    packets = _leading_packets(_armored_body(head) if head.startswith(ARMOR_HEADER) else head)
    tags = [tag for tag, _content in packets]
    key_ids = [content[1:9].hex().upper() for tag, content in packets if tag == KEY_PACKET and len(content) >= 9 and content[0] == 3]
    method: LockMethod = "key" if KEY_PACKET in tags else "password" if PASSWORD_PACKET in tags else "unknown" if DATA_PACKETS.intersection(tags) else "none"
    return {"method": method, "key_ids": key_ids, "have_key": any(key_id in secret_ids for key_id in key_ids)}


def _decrypted_default(source: Path) -> tuple[Path | None, str]:
    inner_name = source.name.removesuffix(".gpg")
    archive_suffix = _match_archive_suffix(inner_name) or ""
    stripped = inner_name.removesuffix(archive_suffix)
    return (None if stripped == "" else source.parent / stripped), archive_suffix


# What the encrypt or decrypt command would do with this path, worked out with the command's own naming and its own check of the result's place.
def look_at(mode: LockerMode, source: Path, compression: FolderArchiveFormat, output: Path | None, secret_ids: frozenset[str]) -> LookView:
    measure = measure_path(source, limit=FOLDER_MEASURE_LIMIT)
    encrypted: EncryptedView = sniff_encrypted(source, secret_ids=secret_ids) if measure["kind"] == "file" else {"method": "none", "key_ids": [], "have_key": False}
    view: LookView = {"source": measure, "encrypted": encrypted, "output": "", "default_output": "", "unpacks": "", "problem": None}
    if measure["kind"] in ("missing", "other"):
        return {**view, "problem": "missing"}
    if mode == "encrypt":
        default_output = _default_encrypted_output(source, compression=compression)
    else:
        if measure["kind"] != "file":
            return {**view, "problem": "not_file"}
        if source.suffix != ".gpg":
            return {**view, "problem": "not_gpg_name"}
        found, view["unpacks"] = _decrypted_default(source)
        if found is None:
            return {**view, "problem": "no_name"}
        default_output = found
    result = default_output if output is None else output
    view.update(output=str(result), default_output=str(default_output))
    try:
        validate_output(source=source, output_path=result, overwrite=False)
    except FileExistsError:
        return {**view, "problem": "exists"}
    except ValueError:
        return {**view, "problem": "overlap"}
    return view
