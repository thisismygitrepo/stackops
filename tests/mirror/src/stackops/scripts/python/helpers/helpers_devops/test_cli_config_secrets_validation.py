import pytest

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_validation import is_valid_env_name


@pytest.mark.parametrize(
    ("name", "expected"),
    (
        ("API_TOKEN", True),
        ("_", True),
        ("a1", True),
        ("", False),
        ("1TOKEN", False),
        ("API-TOKEN", False),
        ("API TOKEN", False),
        ("ÅPI_TOKEN", False),
    ),
)
def test_is_valid_env_name(name: str, expected: bool) -> None:
    assert is_valid_env_name(name) is expected
