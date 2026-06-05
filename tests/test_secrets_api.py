import inspect
import json
from pathlib import Path
from typing import get_type_hints

import pytest
from typer.testing import CliRunner

import stackops.secrets as secrets_api
from stackops.secrets import (
    Login,
    SecretsFileError,
    search_secrets,
)


def test_python_secrets_api_exposes_strict_selectors_only() -> None:
    parameters = inspect.signature(search_secrets).parameters

    assert "terms" not in parameters
    assert "query" not in parameters
    assert "interactive" not in parameters
    assert {"login_name", "profile", "secret_name", "tags", "login_tags", "secret_tags", "scopes", "keys"} <= set(parameters)
    assert "entry_name" not in parameters
    assert "entry_tags" not in parameters
    assert get_type_hints(search_secrets)["return"] == list[Login]
    assert not hasattr(secrets_api, "Entry")
    assert not hasattr(secrets_api, "Account")


def test_python_secrets_api_returns_schema_entries_with_exact_selectors() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        entries = search_secrets(login_name="aws-dev", secret_tags=("iam-access-key",))

        assert entries == [
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
                    }
                ],
            }
        ]


def test_python_secrets_api_returns_each_matching_secret_bundle_as_one_entry() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        entries = search_secrets(login_name="aws-dev")

        assert len(entries) == 2
        assert [entry["secrets"][0]["keyValues"] for entry in entries] == [
            {
                "AWS_ACCESS_KEY_ID": "AKIA_TEST",
                "AWS_SECRET_ACCESS_KEY": "secret-value",
                "AWS_DEFAULT_REGION": "us-east-1",
            },
            {"AWS_SESSION_TOKEN": "session-value"},
        ]


def test_python_secrets_api_filters_by_exact_profile() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        entries = search_secrets(profile="dev", secret_tags=("session-token",))

        assert len(entries) == 1
        assert entries[0]["name"] == "aws-dev"
        assert entries[0]["profile"] == "dev"
        assert entries[0]["secrets"][0]["keyValues"] == {"AWS_SESSION_TOKEN": "session-value"}


def test_python_secrets_api_uses_custom_path() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        custom_path = Path("private") / "team-secrets.json"
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        custom_path.write_text(json.dumps(_secrets_payload()), encoding="utf-8")

        entries = search_secrets(path=custom_path, login_name="github-personal")

        assert entries[0]["secrets"][0]["keyValues"]["GITHUB_TOKEN"] == "ghp_test"


def test_python_secrets_api_returns_all_secret_bundles_without_selectors() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        entries = search_secrets()

        assert len(entries) == 3


def test_python_secrets_api_is_case_sensitive_and_exact() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        assert search_secrets(login_name="AWS-DEV", secret_tags=("iam-access-key",)) == []
        assert search_secrets(profile="DEV") == []


def test_python_secrets_api_rejects_old_singular_scope_field() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        secret = payload["entries"][0]["secrets"][0]  # type: ignore[index]
        secret["scope"] = "repo"  # type: ignore[index]
        del secret["scopes"]  # type: ignore[index]
        _write_secrets_file(payload)

        with pytest.raises(SecretsFileError, match=r"unknown key\(s\): scope"):
            search_secrets(login_name="github-personal")


def test_python_secrets_api_requires_account_name() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        del payload["entries"][0]["name"]  # type: ignore[index]
        _write_secrets_file(payload)

        with pytest.raises(SecretsFileError, match=r"entries\[0\]\.name must be a non-empty string"):
            search_secrets(login_name="github-personal")


def test_python_secrets_api_requires_scopes_array() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        payload["entries"][0]["secrets"][0]["scopes"] = "repo"  # type: ignore[index]
        _write_secrets_file(payload)

        with pytest.raises(SecretsFileError, match=r"scopes must be an array"):
            search_secrets(login_name="github-personal")


def test_python_secrets_api_allows_missing_scopes() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        del payload["entries"][0]["secrets"][0]["scopes"]  # type: ignore[index]
        _write_secrets_file(payload)

        assert search_secrets(login_name="github-personal")[0]["secrets"][0]["keyValues"] == {"GITHUB_TOKEN": "ghp_test"}

        assert search_secrets(login_name="github-personal", scopes=("repo",)) == []


def test_python_secrets_api_preserves_login_notes_for_bitwarden_compatibility() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        payload["entries"][0]["notes"] = "Bitwarden notes"  # type: ignore[index]
        _write_secrets_file(payload)

        entries = search_secrets(login_name="github-personal")

        assert entries[0]["notes"] == "Bitwarden notes"


def test_python_secrets_api_rejects_secret_notes() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        payload["entries"][0]["secrets"][0]["notes"] = "Secret notes"  # type: ignore[index]
        _write_secrets_file(payload)

        with pytest.raises(SecretsFileError, match=r"unknown key\(s\): notes"):
            search_secrets(login_name="github-personal")


def test_python_secrets_api_allows_empty_tags_and_scopes_arrays() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        payload["entries"][0]["tags"] = []  # type: ignore[index]
        payload["entries"][0]["secrets"][0]["tags"] = []  # type: ignore[index]
        payload["entries"][0]["secrets"][0]["scopes"] = []  # type: ignore[index]
        _write_secrets_file(payload)

        entries = search_secrets(login_name="github-personal")

        assert entries == [
            {
                "name": "github-personal",
                "tags": [],
                "username": "octocat",
                "secrets": [
                    {
                        "tags": [],
                        "scopes": [],
                        "keyValues": {"GITHUB_TOKEN": "ghp_test"},
                    }
                ],
            }
        ]
        assert search_secrets(login_name="github-personal", tags=("github",)) == []
        assert search_secrets(login_name="github-personal", secret_tags=("personal-access-token",)) == []
        assert search_secrets(login_name="github-personal", scopes=("repo",)) == []


def test_python_secrets_api_allows_missing_secret_tags_and_preserves_arbitrary_keyvalues() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        payload = _secrets_payload()
        secret = payload["entries"][0]["secrets"][0]  # type: ignore[index]
        del secret["tags"]  # type: ignore[index]
        secret["keyValues"] = {  # type: ignore[index]
            "": "",
            "PORT": 5432,
            "FEATURE_ENABLED": True,
            "SETTINGS": {"nested": [1, None, "x"]},
        }
        _write_secrets_file(payload)

        entries = search_secrets(login_name="github-personal", keys=("",))

        assert entries[0]["secrets"][0]["tags"] == []
        assert entries[0]["secrets"][0]["keyValues"] == {
            "": "",
            "PORT": 5432,
            "FEATURE_ENABLED": True,
            "SETTINGS": {"nested": [1, None, "x"]},
        }


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
