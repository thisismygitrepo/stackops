from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

import stackops.cluster.remote.file_manager as file_manager_module
from stackops.cluster.remote.file_manager import FileManager
from stackops.cluster.remote.models import JobStatus
from stackops.utils.files.read import read_json
from stackops.utils.io import save_json


def _patch_file_manager_paths(monkeypatch: pytest.MonkeyPatch, root: Path) -> tuple[Path, Path, Path]:
    running_path = root / "running_jobs.json"
    queue_path = root / "queued_jobs.json"
    history_path = root / "history_jobs.json"
    monkeypatch.setattr(file_manager_module, "RUNNING_PATH", running_path)
    monkeypatch.setattr(file_manager_module, "QUEUE_PATH", queue_path)
    monkeypatch.setattr(file_manager_module, "HISTORY_PATH", history_path)
    return running_path, queue_path, history_path


def test_from_json_file_round_trip_and_get_fire_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fm = FileManager(job_id="job-1", remote_machine_type="Linux", lock_resources=True, max_simultaneous_jobs=2, base=str(tmp_path))
    payload_path = tmp_path / "file_manager.json"
    save_json(obj=fm.to_dict(), path=payload_path, indent=2, verbose=False)

    restored = FileManager.from_json_file(payload_path)
    monkeypatch.setattr(file_manager_module.platform, "system", lambda: "Windows")

    assert restored.job_root == tmp_path / "queued" / "job-1"
    assert restored.shell_script_path.suffix == ".sh"
    assert restored.get_fire_command().endswith("cluster_script.ps1")


def test_get_job_status_marks_failed_when_running_pid_missing(tmp_path: Path) -> None:
    fm = FileManager(job_id="job-2", remote_machine_type="Linux", lock_resources=True, max_simultaneous_jobs=1, base=str(tmp_path))
    log_dir = fm.execution_log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "status.txt").write_text("running", encoding="utf-8")

    status = fm.get_job_status(session_name="sess", tab_name="tab")

    assert status == "failed"
    assert (log_dir / "status.txt").read_text(encoding="utf-8") == "failed"


def test_unlock_resources_removes_running_job_and_appends_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    running_path, _queue_path, history_path = _patch_file_manager_paths(monkeypatch=monkeypatch, root=tmp_path)
    fm = FileManager(job_id="job-3", remote_machine_type="Linux", lock_resources=True, max_simultaneous_jobs=1, base=str(tmp_path))
    fm.submission_time = datetime(2024, 1, 1, tzinfo=UTC)
    start_time = datetime(2024, 1, 1, 0, 5, tzinfo=UTC)
    save_json(
        obj=[JobStatus(pid=123, job_id="job-3", status="locked", submission_time=fm.submission_time, start_time=start_time).to_dict()],
        path=running_path,
        indent=2,
        verbose=False,
    )
    fm.execution_log_dir.mkdir(parents=True, exist_ok=True)
    (fm.execution_log_dir / "start_time.txt").write_text(start_time.isoformat(), encoding="utf-8")

    fm.unlock_resources()

    assert read_json(running_path) == []
    history = read_json(history_path)
    assert len(history) == 1
    assert history[0]["job_id"] == "job-3"
    assert history[0]["start_time"] == start_time.isoformat()
