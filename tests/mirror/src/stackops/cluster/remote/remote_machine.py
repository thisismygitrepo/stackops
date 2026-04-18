from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import stackops.cluster.remote.remote_machine as remote_machine_module
from stackops.cluster.remote.file_manager import FileManager
from stackops.cluster.remote.job_params import JobParams
from stackops.cluster.remote.models import RemoteStackOpsConfig, WorkloadParams
from stackops.cluster.remote.remote_machine import RemoteMachine
from stackops.utils.files.read import read_json


def _sample_task(*, value: int) -> int:
    return value + 1


def test_init_rejects_duplicate_workload_params_sources(tmp_path: Path) -> None:
    workload = WorkloadParams.default()
    config = RemoteStackOpsConfig(job_id="job-1", base_dir=str(tmp_path), workload_params=workload)

    with pytest.raises(ValueError, match="workload_params provided in both"):
        RemoteMachine(
            func=_sample_task,
            config=config,
            func_kwargs={"workload_params": workload},
            data=None,
        )


def test_generate_scripts_writes_expected_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config = RemoteStackOpsConfig(
        job_id="job-2",
        base_dir=str(tmp_path),
        description="demo",
        notify_upon_completion=True,
        to_email="ops@example.com",
        email_config_name="alerts",
    )
    rm = RemoteMachine(func=_sample_task, config=config, func_kwargs={"value": 2}, data=["input.txt"])
    monkeypatch.setattr(remote_machine_module, "randstr", lambda *args, **kwargs: "token")

    rm.generate_scripts()

    job_params_json = read_json(rm.file_manager.job_root / "data" / "job_params.json")
    py_script = rm.file_manager.py_script_path.expanduser().read_text(encoding="utf-8")
    shell_script = rm.file_manager.shell_script_path.expanduser().read_text(encoding="utf-8")

    assert rm.scripts_generated is True
    assert rm.file_manager.py_script_path.expanduser().exists()
    assert rm.file_manager.shell_script_path.expanduser().exists()
    assert (rm.file_manager.execution_log_dir / "status.txt").read_text(encoding="utf-8") == "queued"
    assert job_params_json["session_name"] == "TS-token"
    assert "Notification email sent to `ops@example.com`." in py_script
    assert "res = func(**func_kwargs)" in py_script
    assert f"cd {rm.job_params.repo_path_rh}" in shell_script


def test_check_job_status_returns_results_path_for_completed_local_job(tmp_path: Path) -> None:
    config = RemoteStackOpsConfig(job_id="job-3", base_dir=str(tmp_path))
    rm = RemoteMachine(func=_sample_task, config=config, func_kwargs={"value": 2}, data=None)
    rm.submitted = True
    rm.file_manager.execution_log_dir.mkdir(parents=True, exist_ok=True)
    results_path = tmp_path / "results"
    results_path.mkdir()
    (rm.file_manager.execution_log_dir / "end_time.txt").write_text("2024-01-01 00:00:00", encoding="utf-8")
    (rm.file_manager.execution_log_dir / "results_folder_path.txt").write_text(str(results_path), encoding="utf-8")

    returned = rm.check_job_status()

    assert returned == results_path
    assert rm.results_path == results_path


def test_build_shell_script_includes_requested_repo_steps(tmp_path: Path) -> None:
    job_params = JobParams.empty()
    job_params.repo_path_rh = "~/repo"
    config = RemoteStackOpsConfig(
        job_id="job-4",
        base_dir=str(tmp_path),
        update_repo=True,
        install_repo=True,
        interactive=True,
    )
    file_manager = FileManager(
        job_id="job-4",
        remote_machine_type="Linux",
        lock_resources=True,
        max_simultaneous_jobs=1,
        base=str(tmp_path),
    )

    build_shell_script = cast(
        Callable[..., str],
        getattr(remote_machine_module, "_build_shell_script"),
    )
    shell_script = build_shell_script(job_params=job_params, config=config, file_manager=file_manager)

    assert "git pull" in shell_script
    assert "pip install -e ." in shell_script
    assert "python -i" in shell_script
