import pytest

from stackops.utils.cloud.encryption import parse_encryption_mode


def test_parse_encryption_mode_accepts_aliases() -> None:
    assert parse_encryption_mode("s") == "symmetric"
    assert parse_encryption_mode("a") == "asymmetric"


def test_parse_encryption_mode_rejects_unknown_alias() -> None:
    with pytest.raises(ValueError, match="symmetric, s, asymmetric, a"):
        parse_encryption_mode("x")
