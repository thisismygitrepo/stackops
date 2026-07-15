import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets
from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
from stackops.secrets.models import SecretsFile, SecretValueMap


def _write_cloudflare_secrets(secrets_path: Path, api_email: str, global_email: str) -> None:
    secrets_file: SecretsFile = {
        "version": "0.5",
        "entries": [
            {
                "name": "cloudflare",
                "secrets": [
                    {
                        "name": "API_TOKEN",
                        "tags": [],
                        "scopes": [],
                        "keyValues": {
                            "CLOUDFLARE_EMAIL": api_email,
                            "CLOUDFLARE_API_TOKEN": "api-token-secret",
                        },
                    },
                    {
                        "name": "global_api_key",
                        "tags": [],
                        "scopes": [],
                        "keyValues": {
                            "CLOUDFLARE_EMAIL": global_email,
                            "GLOBAL_API_KEY": "global-key-secret",
                        },
                    },
                ],
            }
        ],
    }
    secrets_path.write_text(json.dumps(secrets_file), encoding="utf-8")


@pytest.fixture
def captured_handoffs(monkeypatch: pytest.MonkeyPatch) -> list[SecretValueMap]:
    handoffs: list[SecretValueMap] = []

    def capture_handoff(key_values: Mapping[str, object]) -> None:
        handoffs.append(dict(key_values))

    monkeypatch.setattr(secret_actions, "write_env_handoff", capture_handoff)
    return handoffs


@pytest.mark.parametrize("all_matches_option", ("--all-matches", "-a"))
def test_search_all_matches_declares_every_matching_bundle(
    all_matches_option: str,
    tmp_path: Path,
    captured_handoffs: list[SecretValueMap],
) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="alex@example.com", global_email="alex@example.com")

    result = CliRunner().invoke(
        cli_config_secrets.get_app(),
        ["search", "cloudf", all_matches_option, "--source", "local", "--path", str(secrets_path)],
    )

    assert result.exit_code == 0, result.output
    assert captured_handoffs == [
        {
            "CLOUDFLARE_EMAIL": "alex@example.com",
            "CLOUDFLARE_API_TOKEN": "api-token-secret",
            "GLOBAL_API_KEY": "global-key-secret",
        }
    ]
    assert "Prepared 3 env variable(s) from 2 matching secret bundle(s)" in result.output


def test_search_still_rejects_ambiguous_matches_without_all_matches(
    tmp_path: Path,
    captured_handoffs: list[SecretValueMap],
) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="alex@example.com", global_email="alex@example.com")

    result = CliRunner().invoke(
        cli_config_secrets.get_app(),
        ["search", "cloudf", "--source", "local", "--path", str(secrets_path)],
    )

    assert result.exit_code == 1
    assert "Selection did not identify a unique keyValues entry" in result.output
    assert captured_handoffs == []


def test_search_all_matches_rejects_conflicting_duplicate_env_values(
    tmp_path: Path,
    captured_handoffs: list[SecretValueMap],
) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="first@example.com", global_email="second@example.com")

    result = CliRunner().invoke(
        cli_config_secrets.get_app(),
        ["search", "cloudf", "--all-matches", "--source", "local", "--path", str(secrets_path)],
    )

    assert result.exit_code == 1
    assert "conflicting values for environment variable(s): CLOUDFLARE_EMAIL" in result.output
    assert "first@example.com" not in result.output
    assert "second@example.com" not in result.output
    assert captured_handoffs == []


def test_search_rejects_all_matches_with_interactive_before_loading_sources(captured_handoffs: list[SecretValueMap]) -> None:
    result = CliRunner().invoke(cli_config_secrets.get_app(), ["search", "cloudf", "--all-matches", "--interactive"])

    assert result.exit_code == 1
    assert "--all-matches/-a cannot be combined with --interactive/-i" in result.output
    assert captured_handoffs == []


def test_search_all_matches_still_requires_a_selector(tmp_path: Path, captured_handoffs: list[SecretValueMap]) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="alex@example.com", global_email="alex@example.com")

    result = CliRunner().invoke(
        cli_config_secrets.get_app(),
        ["search", "--all-matches", "--source", "local", "--path", str(secrets_path)],
    )

    assert result.exit_code == 1
    assert "Pass at least one term or exact selector" in result.output
    assert captured_handoffs == []
