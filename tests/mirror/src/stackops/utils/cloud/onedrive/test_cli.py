import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.secrets.models import SecretsFile
from stackops.utils.cloud.onedrive import cli as onedrive_cli


def _write_unrelated_secrets_file(secrets_path: Path) -> None:
    secrets_file: SecretsFile = {
        "version": "0.5",
        "entries": [
            {
                "name": "unrelated",
                "secrets": [{"name": "token", "tags": [], "scopes": [], "keyValues": {"UNRELATED_TOKEN": "secret"}}],
            }
        ],
    }
    secrets_path.write_text(json.dumps(secrets_file), encoding="utf-8")


def test_add_prompts_for_account_details_and_accounts_lists_the_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    secrets_path = tmp_path / "secrets.json"
    _write_unrelated_secrets_file(secrets_path)
    monkeypatch.setattr(onedrive_cli, "SECRETS_DOFILE", secrets_path)
    runner = CliRunner()

    add_result = runner.invoke(onedrive_cli.get_app(), ["add"], input="odp\napplication-client-id\n")
    alias_add_result = runner.invoke(
        onedrive_cli.get_app(),
        ["n", "--account-name", "personal", "--client-id", "personal-client-id"],
    )
    accounts_result = runner.invoke(onedrive_cli.get_app(), ["accounts"])
    alias_accounts_result = runner.invoke(onedrive_cli.get_app(), ["r"])

    assert add_result.exit_code == 0, add_result.output
    assert "OneDrive account name" in add_result.output
    assert "Microsoft Application (client) ID" in add_result.output
    assert f"Added OneDrive CLI account 'odp' to {secrets_path}." in add_result.output
    assert "Next: cloud onedrive auth --account-name odp" in add_result.output
    assert alias_add_result.exit_code == 0, alias_add_result.output
    assert f"Added OneDrive CLI account 'personal' to {secrets_path}." in alias_add_result.output
    assert accounts_result.exit_code == 0, accounts_result.output
    assert "ACCOUNT" in accounts_result.output
    assert "AUTHENTICATION" in accounts_result.output
    assert "odp" in accounts_result.output
    assert "personal" in accounts_result.output
    assert accounts_result.output.count("required") == 2
    assert "application-client-id" not in accounts_result.output
    assert alias_accounts_result.exit_code == 0, alias_accounts_result.output
    assert alias_accounts_result.output == accounts_result.output


def test_help_exposes_account_creation_and_listing_commands() -> None:
    result = CliRunner().invoke(onedrive_cli.get_app(), ["--help"])

    assert result.exit_code == 0, result.output
    assert "add" in result.output
    assert "<n>" in result.output
    assert "Add a OneDrive CLI account" in result.output
    assert "accounts" in result.output
    assert "<r>" in result.output
    assert "List defined OneDrive CLI accounts" in result.output
