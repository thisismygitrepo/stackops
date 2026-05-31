import inspect
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.secrets import (
    SecretAmbiguousError,
    SecretLookupError,
    SecretNotFoundError,
    SecretsFileError,
    load_secret_value,
    load_secret_values,
)


def test_python_secrets_api_exposes_strict_selectors_only() -> None:
    parameters = inspect.signature(load_secret_values).parameters

    assert "terms" not in parameters
    assert "query" not in parameters
    assert "interactive" not in parameters
    assert {"entry_name", "secret_name", "tags", "entry_tags", "secret_tags", "scopes", "keys"} <= set(parameters)


def test_python_secrets_api_returns_secret_values_with_exact_selectors() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        values = load_secret_values(entry_name="aws-dev", secret_tags=("iam-access-key",))

        assert values == {
            "AWS_ACCESS_KEY_ID": "AKIA_TEST",
            "AWS_SECRET_ACCESS_KEY": "secret-value",
            "AWS_DEFAULT_REGION": "us-east-1",
        }


def test_python_secrets_api_returns_one_secret_value() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        value = load_secret_value("AWS_SESSION_TOKEN", entry_name="aws-dev")

        assert value == "session-value"


def test_python_secrets_api_uses_custom_path() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        custom_path = Path("private") / "team-secrets.json"
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        custom_path.write_text(json.dumps(_secrets_payload()), encoding="utf-8")

        assert load_secret_value("GITHUB_TOKEN", path=custom_path, entry_name="github-personal") == "ghp_test"


def test_python_secrets_api_requires_at_least_one_exact_selector() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        with pytest.raises(SecretLookupError, match="at least one exact selector"):
            load_secret_values()


def test_python_secrets_api_is_case_sensitive_and_exact() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        with pytest.raises(SecretNotFoundError):
            load_secret_values(entry_name="AWS-DEV", secret_tags=("iam-access-key",))


def test_python_secrets_api_rejects_ambiguous_selection_without_secret_values() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        with pytest.raises(SecretAmbiguousError) as exc_info:
            load_secret_values(entry_name="aws-dev")

        message = str(exc_info.value)
        assert "matched 2 keyValues entries" in message
        assert "aws-dev / iam-access-key -> AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION" in message
        assert "aws-dev / session-token -> AWS_SESSION_TOKEN" in message
        assert "AKIA_TEST" not in message
        assert "secret-value" not in message
        assert "session-value" not in message


def test_python_secrets_api_rejects_old_singular_scope_field() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        secret = payload["entries"][0]["secrets"][0]  # type: ignore[index]
        secret["scope"] = "repo"  # type: ignore[index]
        del secret["scopes"]  # type: ignore[index]
        _write_secrets_file(payload)

        with pytest.raises(SecretsFileError, match=r"unknown key\(s\): scope"):
            load_secret_values(entry_name="github-personal")


def test_python_secrets_api_requires_scopes_array() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        payload["entries"][0]["secrets"][0]["scopes"] = "repo"  # type: ignore[index]
        _write_secrets_file(payload)

        with pytest.raises(SecretsFileError, match=r"scopes must be an array"):
            load_secret_values(entry_name="github-personal")


def _write_secrets_file(payload: dict[str, object]) -> None:
    secrets_path = Path(".stackops") / "secrets" / "secrets.json"
    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    secrets_path.write_text(json.dumps(payload), encoding="utf-8")


def _secrets_payload() -> dict[str, object]:
    return {
        "version": "0.3",
        "entries": [
            {
                "name": "github-personal",
                "tags": ["github", "personal"],
                "username": "octocat",
                "secrets": [
                    {
                        "tags": ["personal-access-token"],
                        "scopes": ["repo", "workflow"],
                        "keyValues": {"GITHUB_TOKEN": "ghp_test"},
                    }
                ],
            },
            {
                "name": "aws-dev",
                "tags": ["aws", "dev"],
                "profile": "dev",
                "secrets": [
                    {
                        "tags": ["iam-access-key"],
                        "scopes": ["development"],
                        "keyValues": {
                            "AWS_ACCESS_KEY_ID": "AKIA_TEST",
                            "AWS_SECRET_ACCESS_KEY": "secret-value",
                            "AWS_DEFAULT_REGION": "us-east-1",
                        },
                    },
                    {
                        "tags": ["session-token"],
                        "scopes": ["development"],
                        "keyValues": {"AWS_SESSION_TOKEN": "session-value"},
                    },
                ],
            },
        ],
    }
