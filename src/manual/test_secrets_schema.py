import json
from pathlib import Path

import pytest

from stackops.secrets.loader import SecretsSchemaError, load_secrets_file
from stackops.secrets.models import SecretRecord


REPO_ROOT = Path(__file__).resolve().parents[2]
SECRETS_SCHEMA_PATH = REPO_ROOT / "src" / "stackops" / "secrets" / "secrets.schema.json"
SECRETS_EXAMPLE_PATH = REPO_ROOT / "src" / "stackops" / "secrets" / "secrets.example.json"


def test_loader_requires_secret_name(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(
        json.dumps({"version": "0.5", "entries": [{"name": "service", "secrets": [{"keyValues": {"TOKEN": "redacted"}}]}]}), encoding="utf-8"
    )

    with pytest.raises(SecretsSchemaError, match=r"entries\[0\]\.secrets\[0\]\.name must be a non-empty string"):
        load_secrets_file(secrets_path)


def test_loaded_secret_name_is_required_type(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(
        json.dumps({"version": "0.5", "entries": [{"name": "service", "secrets": [{"name": "api-token", "keyValues": {"TOKEN": "redacted"}}]}]}),
        encoding="utf-8",
    )

    loaded = load_secrets_file(secrets_path)
    secret: SecretRecord = loaded["entries"][0]["secrets"][0]

    assert secret["name"] == "api-token"


def test_schema_requires_secret_name() -> None:
    schema = json.loads(SECRETS_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["definitions"]["secret"]["required"] == ["name", "keyValues"]


def test_packaged_example_secret_entries_have_names() -> None:
    example = json.loads(SECRETS_EXAMPLE_PATH.read_text(encoding="utf-8"))

    assert all("name" in secret for entry in example["entries"] for secret in entry["secrets"])
