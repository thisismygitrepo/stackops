from pathlib import Path

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python.helpers.helpers_devops import cli_backup_retrieve, cli_data, devops_status_checks


def test_sync_exits_cleanly_when_backup_config_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(cli_backup_retrieve, "read_backup_config", lambda repo: None)
    monkeypatch.setattr(
        cli_backup_retrieve,
        "describe_missing_backup_config",
        lambda repo: "User backup configuration file does not exist: /tmp/missing.yaml",
    )

    result = runner.invoke(cli_data.get_app(), ["sync", "up", "--repo", "user"])

    assert result.exit_code == 1
    assert "User backup configuration file does not exist: /tmp/missing.yaml" in result.stdout


def test_register_backup_entry_fails_when_existing_user_config_cannot_load(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_path = tmp_path.joinpath("data.txt")
    local_path.write_text("payload", encoding="utf-8")
    config_path = tmp_path.joinpath("mapper_data.yaml")
    config_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(cli_backup_retrieve, "USER_BACKUP_PATH", config_path)
    monkeypatch.setattr(cli_backup_retrieve, "read_backup_config", lambda repo: None)
    monkeypatch.setattr(
        cli_backup_retrieve,
        "describe_missing_backup_config",
        lambda repo: f"User backup configuration file is empty or invalid: {config_path}",
    )

    with pytest.raises(ValueError, match="empty or invalid"):
        cli_backup_retrieve.register_backup_entry(path_local=str(local_path), group="default", os="linux")


def test_check_backup_config_handles_unloadable_library_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from machineconfig.scripts.python.helpers.helpers_devops import backup_config

    config_path = tmp_path.joinpath("mapper_data.yaml")
    config_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(backup_config, "LIBRARY_BACKUP_PATH", config_path)
    monkeypatch.setattr(backup_config, "read_backup_config", lambda repo: None)

    status = devops_status_checks.check_backup_config()

    assert status["backup_items_count"] == 0
    assert status["backup_items"] == []