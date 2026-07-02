from collections.abc import Mapping
from typing import cast

import pytest
import yaml

from stackops.scripts.python.helpers.helpers_cloud import backup_config
from stackops.utils.cloud.encryption import EncryptionMode


SAMPLE_ENTRY_FIELDS: dict[str, object] = {
    "path_local": "~/example.txt",
    "path_cloud": "^",
    "share_url": None,
    "zip": False,
    "rel2home": True,
    "os": ["linux"],
}


@pytest.mark.parametrize("encryption", ("symmetric", "asymmetric", None))
def test_backup_config_parses_and_serializes_canonical_encryption(encryption: EncryptionMode | None) -> None:
    entry: dict[str, object] = {**SAMPLE_ENTRY_FIELDS, "encryption": encryption}
    raw: dict[str, object] = {"example_group": {"sample_item": entry}}

    parsed = backup_config._parse_backup_config(raw)
    serialized = backup_config.serialize_backup_config(parsed)
    serialized_raw = cast(object, yaml.safe_load(serialized))

    assert parsed["example_group"]["sample_item"]["encryption"] == encryption
    assert f"encryption: {encryption or 'null'}" in serialized
    assert "encrypt:" not in serialized
    assert isinstance(serialized_raw, Mapping)
    assert backup_config._parse_backup_config({str(key): value for key, value in serialized_raw.items()}) == parsed


def test_backup_config_requires_encryption_field() -> None:
    entry = SAMPLE_ENTRY_FIELDS.copy()
    raw: dict[str, object] = {"example_group": {"sample_item": entry}}

    with pytest.raises(ValueError, match="must define 'encryption'"):
        backup_config._parse_backup_config(raw)


def test_backup_config_rejects_encrypt_field() -> None:
    entry: dict[str, object] = {**SAMPLE_ENTRY_FIELDS, "encrypt": False, "encryption": None}
    raw: dict[str, object] = {"example_group": {"sample_item": entry}}

    with pytest.raises(ValueError, match="unsupported fields: encrypt"):
        backup_config._parse_backup_config(raw)


def test_backup_config_rejects_encryption_alias() -> None:
    entry: dict[str, object] = {**SAMPLE_ENTRY_FIELDS, "encryption": "s"}
    raw: dict[str, object] = {"example_group": {"sample_item": entry}}

    with pytest.raises(ValueError, match="encryption must be symmetric, asymmetric, or null"):
        backup_config._parse_backup_config(raw)


def test_packaged_library_backup_config_parses_without_user_config_access() -> None:
    parsed = backup_config.load_backup_config_file(backup_config.LIBRARY_BACKUP_PATH, empty_as_config=False)

    assert parsed is not None
    assert parsed
