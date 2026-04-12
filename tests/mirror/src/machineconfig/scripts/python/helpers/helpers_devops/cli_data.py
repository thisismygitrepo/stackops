from pathlib import Path
import shutil
import subprocess

import pytest
import typer

import machineconfig.scripts.python.helpers.helpers_devops.backup_config as backup_config_module
import machineconfig.scripts.python.helpers.helpers_devops.cli_backup_retrieve as cli_backup_retrieve_module
import machineconfig.scripts.python.helpers.helpers_devops.cli_data as cli_data_module


def test_sync_maps_direction_and_calls_backup_retrieve(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str | None, str | None, str]] = []

    def fake_main_backup_retrieve(direction: str, which: str | None, cloud: str | None, repo: str) -> None:
        calls.append((direction, which, cloud, repo))

    monkeypatch.setattr(cli_backup_retrieve_module, "main_backup_retrieve", fake_main_backup_retrieve)

    cli_data_module.sync(direction="u", cloud="maincloud", which="all", repo="user")

    assert calls == [("BACKUP", "all", "maincloud", "user")]


def test_register_data_reports_added_and_updated_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    results = iter([(Path("/tmp/backup.yaml"), "entry_one", False), (Path("/tmp/backup.yaml"), "entry_one", True)])

    def fake_register_backup_entry(
        path_local: str, group: str, entry_name: str | None, path_cloud: str | None, zip_: bool, encrypt: bool, rel2home: bool | None, os: str
    ) -> tuple[Path, str, bool]:
        _ = path_local, group, entry_name, path_cloud, zip_, encrypt, rel2home, os
        return next(results)

    monkeypatch.setattr(cli_backup_retrieve_module, "register_backup_entry", fake_register_backup_entry)
    monkeypatch.setattr(cli_data_module.typer, "echo", messages.append)

    cli_data_module.register_data(
        path_local="~/data.txt", group="default", name=None, path_cloud=None, zip_=False, encrypt=False, rel2home=None, os="linux"
    )
    cli_data_module.register_data(
        path_local="~/data.txt", group="default", name=None, path_cloud=None, zip_=False, encrypt=False, rel2home=None, os="linux"
    )

    assert messages == ["Added backup entry 'entry_one' in /tmp/backup.yaml", "Updated backup entry 'entry_one' in /tmp/backup.yaml"]


def test_edit_data_creates_user_file_and_invokes_editor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    user_backup_path = tmp_path / "backup.yaml"
    editor_calls: list[list[str]] = []

    def fake_run(args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        _ = check
        editor_calls.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(backup_config_module, "USER_BACKUP_PATH", user_backup_path)
    monkeypatch.setattr(shutil, "which", lambda editor: f"/bin/{editor}")
    monkeypatch.setattr(subprocess, "run", fake_run)

    cli_data_module.edit_data(editor="hx", repo="user")

    assert user_backup_path.exists()
    assert user_backup_path.read_text(encoding="utf-8") == backup_config_module.DEFAULT_BACKUP_HEADER
    assert editor_calls == [["/bin/hx", str(user_backup_path)]]


def test_edit_data_rejects_missing_library_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backup_config_module, "LIBRARY_BACKUP_PATH", tmp_path / "missing-library.yaml")

    with pytest.raises(typer.Exit) as exit_info:
        cli_data_module.edit_data(editor="hx", repo="library")

    assert exit_info.value.exit_code == 1
