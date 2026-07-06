import base64
import json
from pathlib import Path
from typing import cast


type JsonObject = dict[str, object]


def read_json_object(path: Path) -> JsonObject:
    raw_data = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(raw_data, dict):
        raise ValueError(f"Credential file must contain a JSON object: {path}")
    return cast(JsonObject, raw_data)


def read_optional_json_string(data: JsonObject, keys: tuple[str, ...], path: Path) -> str | None:
    value: object = data
    for key in keys:
        if not isinstance(value, dict):
            raise ValueError(f"Credential field {'.'.join(keys)} has an invalid parent object: {path}")
        if key not in value:
            return None
        value = value[key]

    if not isinstance(value, str) or value == "":
        raise ValueError(f"Credential field {'.'.join(keys)} must be a non-empty string: {path}")
    return value


def decode_jwt_payload(token: str, path: Path) -> JsonObject:
    token_parts = token.split(".")
    if len(token_parts) != 3:
        raise ValueError(f"Credential JWT must contain three sections: {path}")

    payload_text = token_parts[1]
    payload_padding = "=" * (-len(payload_text) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(payload_text + payload_padding)
        raw_payload = cast(object, json.loads(payload_bytes))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Credential JWT payload is invalid: {path}") from error

    if not isinstance(raw_payload, dict):
        raise ValueError(f"Credential JWT payload must contain a JSON object: {path}")
    return cast(JsonObject, raw_payload)
