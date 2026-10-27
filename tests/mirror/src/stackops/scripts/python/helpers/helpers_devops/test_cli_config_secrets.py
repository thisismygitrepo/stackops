import json
from collections.abc import Mapping
from pathlib import Path
from typing import NoReturn

import pytest
from git import Repo
from typer.testing import CliRunner

import stackops.secrets.paths as secrets_paths
from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets
from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_support as secret_support
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import SecretsSource
from stackops.secrets.models import SecretsFile, SecretValueMap
from stackops.utils.repos import stackops_paths


def _write_cloudflare_secrets(secrets_path: Path, api_email: str, global_email: str) -> None:
    secrets_file: SecretsFile = {
        "$schema": "https://example.com/stackops-secrets.schema.json",
        "version": "0.5",
        "entries": [
            {
                "name": "cloudflare",
                "secrets": [
                    {
                        "name": "API_TOKEN",
                        "tags": [],
                        "scopes": [],
                        "keyValues": {"CLOUDFLARE_EMAIL": api_email, "CLOUDFLARE_API_TOKEN": "api-token-secret"},
                    },
                    {
                        "name": "global_api_key",
                        "tags": [],
                        "scopes": [],
                        "keyValues": {"CLOUDFLARE_EMAIL": global_email, "GLOBAL_API_KEY": "global-key-secret"},
                    },
                ],
            }
        ],
    }
    secrets_path.write_text(json.dumps(secrets_file), encoding="utf-8")


@pytest.fixture
def captured_handoffs(monkeypatch: pytest.MonkeyPatch) -> list[SecretValueMap]:
    handoffs: list[SecretValueMap] = []

    def capture_handoff(key_values: Mapping[str, object], *, verbose: bool) -> None:
        _ = verbose
        handoffs.append(dict(key_values))

    monkeypatch.setattr(secret_actions, "write_env_handoff", capture_handoff)
    return handoffs


@pytest.mark.parametrize(("project_exists", "expected_email"), ((True, "project@example.com"), (False, "user@example.com")))
def test_load_without_source_prefers_repository_project_then_user(
    project_exists: bool, expected_email: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_handoffs: list[SecretValueMap]
) -> None:
    Repo.init(tmp_path).close()
    project_path = tmp_path / ".stackops" / "secrets" / "secrets.json"
    if project_exists:
        project_path.parent.mkdir(parents=True)
        _write_cloudflare_secrets(project_path, api_email="project@example.com", global_email="project@example.com")

    user_path = tmp_path / "user-secrets.json"
    _write_cloudflare_secrets(user_path, api_email="user@example.com", global_email="user@example.com")
    monkeypatch.setattr(secrets_paths, "SECRETS_DOFILE", user_path)
    nested_directory = tmp_path / "nested" / "directory"
    nested_directory.mkdir(parents=True)
    monkeypatch.chdir(nested_directory)

    result = CliRunner().invoke(cli_config_secrets.get_app(), ["load", "API_TOKEN"])

    assert result.exit_code == 0, result.output
    assert captured_handoffs == [{"CLOUDFLARE_EMAIL": expected_email, "CLOUDFLARE_API_TOKEN": "api-token-secret"}]
    assert "Prepared 2 environment variables: CLOUDFLARE_EMAIL, CLOUDFLARE_API_TOKEN." in result.output


def test_load_with_missing_custom_path_does_not_fall_back_to_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_handoffs: list[SecretValueMap]
) -> None:
    user_path = tmp_path / "user-secrets.json"
    _write_cloudflare_secrets(user_path, api_email="user@example.com", global_email="user@example.com")
    monkeypatch.setattr(secrets_paths, "SECRETS_DOFILE", user_path)
    missing_path = tmp_path / "missing-secrets.json"

    result = CliRunner().invoke(cli_config_secrets.get_app(), ["load", "API_TOKEN", "--custom-path", str(missing_path)])

    assert result.exit_code == 1
    assert f"Secrets file not found: {missing_path}" in result.output
    assert captured_handoffs == []


@pytest.mark.parametrize("all_matches_option", ("--all-matches", "-a"))
@pytest.mark.parametrize("source", ("project", "user", "all"))
def test_load_all_matches_uses_only_custom_file(
    all_matches_option: str, source: SecretsSource, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, captured_handoffs: list[SecretValueMap],
) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="alex@example.com", global_email="alex@example.com")

    def reject_default_lookup(*_args: object, **_kwargs: object) -> NoReturn:
        raise AssertionError("A custom file must bypass project and user source resolution")

    monkeypatch.setattr(secret_support, "_resolve_user_secrets_path", reject_default_lookup)
    monkeypatch.setattr(stackops_paths, "current_repo_stackops_path", reject_default_lookup)
    monkeypatch.setattr(stackops_paths, "require_current_repo_stackops_path", reject_default_lookup)

    result = CliRunner().invoke(
        cli_config_secrets.get_app(), ["load", "cloudf", all_matches_option, "--verbose", "--source", source, "--custom-path", str(secrets_path)]
    )

    assert result.exit_code == 0, result.output
    assert captured_handoffs == [
        {"CLOUDFLARE_EMAIL": "alex@example.com", "CLOUDFLARE_API_TOKEN": "api-token-secret", "GLOBAL_API_KEY": "global-key-secret"}
    ]
    assert "Prepared 3 environment variables from 2 matching secret bundles" in result.output
    assert "Defining env vars:" not in result.output
    assert "CLOUDFLARE_EMAIL, CLOUDFLARE_API_TOKEN, GLOBAL_API_KEY." in result.output


def test_load_still_rejects_ambiguous_matches_without_all_matches(tmp_path: Path, captured_handoffs: list[SecretValueMap]) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="alex@example.com", global_email="alex@example.com")

    result = CliRunner().invoke(cli_config_secrets.get_app(), ["load", "cloudf", "--source", "project", "--custom-path", str(secrets_path)])

    assert result.exit_code == 1
    assert "Selection did not identify a unique keyValues entry" in result.output
    assert captured_handoffs == []


def test_load_all_matches_rejects_conflicting_duplicate_env_values(tmp_path: Path, captured_handoffs: list[SecretValueMap]) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="first@example.com", global_email="second@example.com")

    result = CliRunner().invoke(cli_config_secrets.get_app(), ["load", "cloudf", "--all-matches", "--source", "project", "--custom-path", str(secrets_path)])

    assert result.exit_code == 1
    assert "Cannot merge 2 matching secret bundles: 1 environment variable would receive different values" in result.output
    assert "--all-matches/-a builds one environment from every match" in result.output
    assert "Conflicting environment variables:\n  CLOUDFLARE_EMAIL" in result.output
    assert "[custom-file] cloudflare / API_TOKEN @ entries[0].secrets[0].keyValues -> CLOUDFLARE_EMAIL" in result.output
    assert "[custom-file] cloudflare / global_api_key @ entries[0].secrets[1].keyValues -> CLOUDFLARE_EMAIL" in result.output
    assert "JSON with every bundle: use devops vault search with --all-matches/-a --json/-j" in result.output
    assert "replace --all-matches/-a with --interactive/-i" in result.output
    assert "--name/-n and --secret-name/-N" in result.output
    assert "rename the conflicting keyValues keys" in result.output
    assert "first@example.com" not in result.output
    assert "second@example.com" not in result.output
    assert captured_handoffs == []


@pytest.mark.parametrize("selection_arguments", (("API_TOKEN",), ("cloudf", "--all-matches")))
def test_search_json_preserves_original_schema_and_filters_only_login_entries(
    selection_arguments: tuple[str, ...], tmp_path: Path, captured_handoffs: list[SecretValueMap]
) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="first@example.com", global_email="second@example.com")

    result = CliRunner().invoke(
        cli_config_secrets.get_app(), ["search", *selection_arguments, "--json", "--source", "project", "--custom-path", str(secrets_path)]
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "$schema": "https://example.com/stackops-secrets.schema.json",
        "version": "0.5",
        "entries": [
            {
                "name": "cloudflare",
                "secrets": [
                    {
                        "name": "API_TOKEN",
                        "tags": [],
                        "scopes": [],
                        "keyValues": {"CLOUDFLARE_EMAIL": "first@example.com", "CLOUDFLARE_API_TOKEN": "api-token-secret"},
                    },
                    {
                        "name": "global_api_key",
                        "tags": [],
                        "scopes": [],
                        "keyValues": {"CLOUDFLARE_EMAIL": "second@example.com", "GLOBAL_API_KEY": "global-key-secret"},
                    },
                ],
            }
        ],
    }
    assert captured_handoffs == []


def test_search_rejects_all_matches_with_interactive_before_loading_sources(captured_handoffs: list[SecretValueMap]) -> None:
    result = CliRunner().invoke(cli_config_secrets.get_app(), ["search", "cloudf", "--all-matches", "--interactive"])

    assert result.exit_code == 1
    assert "--all-matches/-a cannot be combined with --interactive/-i" in result.output
    assert captured_handoffs == []


def test_load_all_matches_still_requires_a_selector(tmp_path: Path, captured_handoffs: list[SecretValueMap]) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="alex@example.com", global_email="alex@example.com")

    result = CliRunner().invoke(cli_config_secrets.get_app(), ["load", "--all-matches", "--source", "project", "--custom-path", str(secrets_path)])

    assert result.exit_code == 1
    assert "Pass at least one term or exact selector" in result.output
    assert captured_handoffs == []


def test_search_lists_env_keys_without_loading_or_printing_values(tmp_path: Path, captured_handoffs: list[SecretValueMap]) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="alex@example.com", global_email="alex@example.com")

    result = CliRunner().invoke(cli_config_secrets.get_app(), ["search", "cloudf", "--all-matches", "--source", "project", "--custom-path", str(secrets_path)])

    assert result.exit_code == 0, result.output
    assert "Environment keys: CLOUDFLARE_EMAIL, CLOUDFLARE_API_TOKEN" in result.output
    assert "Environment keys: CLOUDFLARE_EMAIL, GLOBAL_API_KEY" in result.output
    assert "Nothing was loaded" in result.output
    assert "api-token-secret" not in result.output
    assert "alex@example.com" not in result.output
    assert captured_handoffs == []


def test_load_has_no_json_option(tmp_path: Path, captured_handoffs: list[SecretValueMap]) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_cloudflare_secrets(secrets_path=secrets_path, api_email="alex@example.com", global_email="alex@example.com")

    result = CliRunner().invoke(cli_config_secrets.get_app(), ["load", "API_TOKEN", "--json", "--source", "project", "--custom-path", str(secrets_path)])

    assert result.exit_code == 2
    assert "api-token-secret" not in result.output
    assert captured_handoffs == []
