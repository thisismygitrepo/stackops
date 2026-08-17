import base64
import binascii
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_key_validation import (
    validate_ecdsa_public_point,
    validate_ed25519_public_key,
    validate_rsa_public_numbers,
)


type PublicKeyType = Literal[
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "sk-ecdsa-sha2-nistp256@openssh.com",
    "sk-ssh-ed25519@openssh.com",
    "ssh-ed25519",
    "ssh-rsa",
]


@dataclass(frozen=True, slots=True)
class PublicKeyRecord:
    key_type: PublicKeyType
    text: str


SUPPORTED_KEY_TYPES: frozenset[PublicKeyType] = frozenset(
    {
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "sk-ecdsa-sha2-nistp256@openssh.com",
        "sk-ssh-ed25519@openssh.com",
        "ssh-ed25519",
        "ssh-rsa",
    }
)
PRIVATE_KEY_MARKERS: tuple[str, ...] = (
    " PRIVATE KEY-----",
    "PUTTY-USER-KEY-FILE-",
)


def parse_public_key_records(value: str, source: str) -> list[PublicKeyRecord]:
    upper_value = value.upper()
    if any(marker in upper_value for marker in PRIVATE_KEY_MARKERS):
        raise ValueError(f"{source} contains a private-key marker; refusing to authorize or transmit it.")

    records: list[PublicKeyRecord] = []
    for line_number, raw_line in enumerate(value.splitlines(), start=1):
        line = raw_line.strip()
        if line == "":
            continue
        records.append(_parse_public_key_record(line=line, source=source, line_number=line_number))
    if not records:
        raise ValueError(f"{source} does not contain a public-key record.")
    return records


def read_public_key_file(path: Path) -> list[PublicKeyRecord]:
    if not path.is_file():
        raise ValueError(f"Public-key source is not a file: {path}")
    return parse_public_key_records(value=path.read_text(encoding="utf-8"), source=str(path))


def update_authorized_keys(path: Path, records: Sequence[PublicKeyRecord]) -> int:
    if len(records) == 0:
        raise ValueError("At least one validated public-key record is required.")
    existing_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    known_lines = set(existing_lines)
    updated_lines = list(existing_lines)
    added_count = 0
    for record in records:
        if record.text in known_lines:
            continue
        updated_lines.append(record.text)
        known_lines.add(record.text)
        added_count += 1
    path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8", newline="\n")
    return added_count


def _parse_public_key_record(line: str, source: str, line_number: int) -> PublicKeyRecord:
    if any(ord(character) < 32 or ord(character) == 127 for character in line):
        raise ValueError(f"{source}, line {line_number} contains a control character.")
    parts = line.split(maxsplit=2)
    if len(parts) < 2:
        raise ValueError(f"{source}, line {line_number} is not an SSH public-key record.")

    key_type_text, encoded_key = parts[0:2]
    if key_type_text not in SUPPORTED_KEY_TYPES:
        raise ValueError(f"{source}, line {line_number} uses unsupported SSH key type {key_type_text!r}.")
    key_type = key_type_text
    try:
        padding = "=" * (-len(encoded_key) % 4)
        payload = base64.b64decode(encoded_key + padding, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError(f"{source}, line {line_number} has invalid public-key base64 data.") from error
    canonical_key = base64.b64encode(payload).decode("ascii")
    if encoded_key not in {canonical_key, canonical_key.rstrip("=")}:
        raise ValueError(f"{source}, line {line_number} has non-canonical public-key base64 data.")
    _validate_key_payload(payload=payload, key_type=key_type, source=source, line_number=line_number)

    comment = parts[2].strip() if len(parts) == 3 else ""
    normalized = f"{key_type} {encoded_key}"
    if comment != "":
        normalized = f"{normalized} {comment}"
    return PublicKeyRecord(key_type=key_type, text=normalized)


def _validate_key_payload(payload: bytes, key_type: PublicKeyType, source: str, line_number: int) -> None:
    try:
        encoded_type, offset = _read_ssh_field(payload=payload, offset=0)
        if encoded_type.decode("ascii") != key_type:
            raise ValueError("the encoded and declared key types differ")
        match key_type:
            case "ssh-ed25519":
                public_key, offset = _read_ssh_field(payload=payload, offset=offset)
                validate_ed25519_public_key(public_key=public_key)
            case "ssh-rsa":
                exponent, offset = _read_ssh_field(payload=payload, offset=offset)
                modulus, offset = _read_ssh_field(payload=payload, offset=offset)
                validate_rsa_public_numbers(exponent_field=exponent, modulus_field=modulus)
            case "ecdsa-sha2-nistp256" | "ecdsa-sha2-nistp384" | "ecdsa-sha2-nistp521":
                offset = _validate_ecdsa_fields(payload=payload, offset=offset, key_type=key_type)
            case "sk-ssh-ed25519@openssh.com":
                public_key, offset = _read_ssh_field(payload=payload, offset=offset)
                application, offset = _read_ssh_field(payload=payload, offset=offset)
                validate_ed25519_public_key(public_key=public_key)
                if application == b"":
                    raise ValueError("a security-key Ed25519 record has no application")
            case "sk-ecdsa-sha2-nistp256@openssh.com":
                offset = _validate_ecdsa_fields(payload=payload, offset=offset, key_type="ecdsa-sha2-nistp256")
                application, offset = _read_ssh_field(payload=payload, offset=offset)
                if application == b"":
                    raise ValueError("a security-key ECDSA record has no application")
        if offset != len(payload):
            raise ValueError("the encoded key has trailing data")
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError(f"{source}, line {line_number} has malformed {key_type} key data: {error}.") from error


def _validate_ecdsa_fields(payload: bytes, offset: int, key_type: str) -> int:
    curve_name = key_type.removeprefix("ecdsa-sha2-")
    curve, offset = _read_ssh_field(payload=payload, offset=offset)
    point, offset = _read_ssh_field(payload=payload, offset=offset)
    if curve.decode("ascii") != curve_name:
        raise ValueError("the encoded ECDSA curve differs from the declared key type")
    validate_ecdsa_public_point(curve_name=curve_name, point=point)
    return offset


def _read_ssh_field(payload: bytes, offset: int) -> tuple[bytes, int]:
    length_end = offset + 4
    if length_end > len(payload):
        raise ValueError("an SSH field length is truncated")
    field_length = int.from_bytes(payload[offset:length_end], byteorder="big", signed=False)
    field_end = length_end + field_length
    if field_end > len(payload):
        raise ValueError("an SSH field is truncated")
    return payload[length_end:field_end], field_end
