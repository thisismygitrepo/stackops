import base64
import json
from pathlib import Path

import pytest

from support.json_values import decode_jwt_payload, read_json_object, read_optional_json_string


def _jwt(payload: dict[str, object]) -> str:
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded_payload}.signature"


def test_json_value_helpers_read_nested_strings_and_jwt_claims(tmp_path: Path) -> None:
    credential_path = tmp_path / "auth.json"
    credential_path.write_text('{"tokens": {"account_id": "account-one"}}', encoding="utf-8")
    credential = read_json_object(path=credential_path)

    assert read_optional_json_string(credential, ("tokens", "account_id"), credential_path) == "account-one"
    assert read_optional_json_string(credential, ("tokens", "missing"), credential_path) is None
    assert decode_jwt_payload(token=_jwt({"sub": "user-one"}), path=credential_path) == {"sub": "user-one"}


def test_decode_jwt_payload_rejects_malformed_token(tmp_path: Path) -> None:
    credential_path = tmp_path / "auth.json"

    with pytest.raises(ValueError, match="three sections"):
        decode_jwt_payload(token="not-a-jwt", path=credential_path)

