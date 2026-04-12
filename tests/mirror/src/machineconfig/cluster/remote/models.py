from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import machineconfig.cluster.remote.models as models_module
from machineconfig.cluster.remote.models import JobStatus, RemoteMachineConfig, WorkloadParams


def test_workload_params_split_to_jobs_preserves_complete_range() -> None:
    workload = WorkloadParams(
        idx_min=0,
        idx_max=10,
        idx_start=0,
        idx_end=7,
        idx=0,
        jobs=3,
        job_id="",
    )

    result = workload.split_to_jobs(jobs=3)

    assert [(item.idx_start, item.idx_end) for item in result] == [(0, 2), (2, 4), (4, 7)]


def test_workload_params_get_section_from_series_scales_indices() -> None:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    series = [base + timedelta(hours=index) for index in range(11)]
    workload = WorkloadParams(
        idx_min=0,
        idx_max=10,
        idx_start=2,
        idx_end=5,
        idx=0,
        jobs=1,
        job_id="",
    )

    start, end = workload.get_section_from_series(series)

    assert start == series[2]
    assert end == series[5]


def test_job_status_from_dict_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="Unsupported job status"):
        JobStatus.from_dict(
            {
                "pid": 1,
                "job_id": "job",
                "status": "broken",
                "submission_time": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
                "start_time": None,
            }
        )


def test_remote_machine_config_requires_cloud_name_for_cloud_transfer() -> None:
    with pytest.raises(ValueError, match="cloud_name must be provided"):
        RemoteMachineConfig(transfer_method="cloud")


def test_remote_machine_config_uses_default_notification_values(monkeypatch: pytest.MonkeyPatch) -> None:
    defaults = {"to_email": "ops@example.com", "email_config_name": "alerts"}
    monkeypatch.setattr(models_module, "_read_default_config_value", lambda key: defaults[key])

    config = RemoteMachineConfig(notify_upon_completion=True)

    assert config.to_email == "ops@example.com"
    assert config.email_config_name == "alerts"
