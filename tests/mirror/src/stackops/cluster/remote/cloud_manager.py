

import json
from pathlib import Path

import pytest

import stackops.cluster.remote.cloud_manager as cloud_manager
from stackops.utils import rclone as rclone_utils


def test_format_table_markdown_sorts_columns_and_fills_missing_cells() -> None:
    table = cloud_manager._format_table_markdown([{"b": 2, "a": 1}, {"a": 3}])

    assert table.splitlines() == ["| a | b |", "| --- | --- |", "| 1 | 2 |", "| 3 |  |"]


def test_prepare_servers_report_reads_running_job_counts(tmp_path: Path) -> None:
    workers_root = tmp_path / "workers"
    alpha_dir = workers_root / "alpha"
    beta_dir = workers_root / "beta"
    alpha_dir.mkdir(parents=True)
    beta_dir.mkdir(parents=True)
    (alpha_dir / "running_jobs.json").write_text(json.dumps(["job-a", "job-b"]) + "\n", encoding="utf-8")

    report = cloud_manager._prepare_servers_report(workers_root)
    rows = {str(row["machine"]): row for row in report}

    assert rows["alpha"]["running_jobs"] == 2
    assert rows["beta"]["running_jobs"] == 0
    assert isinstance(rows["alpha"]["last_update"], str)


def test_sync_from_cloud_ignores_missing_remote_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "nested" / "logs.json"

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        assert in_path.startswith("remote:")
        assert out_path == str(path)
        assert transfers == cloud_manager.RCLONE_TRANSFERS
        assert show_command is False
        assert show_progress is False
        raise rclone_utils.RcloneCommandError(command=["rclone", "copyto"], returncode=3, stdout="", stderr="directory not found", hint=None)

    monkeypatch.setattr(cloud_manager.rclone_utils, "copyto", fake_copyto)
    monkeypatch.setattr(cloud_manager.rclone_utils, "is_missing_remote_path_error", lambda _error: True)

    cloud_manager._sync_from_cloud("remote", path)

    assert path.parent.is_dir()


def test_sync_dir_from_cloud_reraises_non_missing_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_sync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
        assert source.startswith("remote:")
        assert target == str(tmp_path)
        assert transfers == cloud_manager.RCLONE_TRANSFERS
        assert delete_during is False
        assert show_command is False
        assert show_progress is False
        raise rclone_utils.RcloneCommandError(command=["rclone", "sync"], returncode=5, stdout="", stderr="permission denied", hint=None)

    monkeypatch.setattr(cloud_manager.rclone_utils, "sync", fake_sync)
    monkeypatch.setattr(cloud_manager.rclone_utils, "is_missing_remote_path_error", lambda _error: False)

    with pytest.raises(rclone_utils.RcloneCommandError):
        cloud_manager._sync_dir_from_cloud("remote", tmp_path)


def test_read_log_creates_default_file_when_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    base_path = tmp_path / "cloud"
    monkeypatch.setattr(cloud_manager.CloudManager, "base_path", base_path)
    monkeypatch.setattr(cloud_manager, "_this_machine", lambda: "tester@node")
    manager = cloud_manager.CloudManager(max_jobs=2, cloud="remote", reset_local=False)
    manager.lock_claimed = True

    log = manager.read_log()

    assert log == {"queued": [], "running": [], "completed": [], "failed": []}
    assert (base_path / "logs.json").is_file()
