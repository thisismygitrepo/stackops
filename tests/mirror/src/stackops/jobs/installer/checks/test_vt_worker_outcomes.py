from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Lock
from typing import TYPE_CHECKING, cast

import pytest

from stackops.jobs.installer.checks import vt_workers
from stackops.jobs.installer.checks.scan_outcomes import ScanCancelled, ScanFailure, ScanOutcome, ScanSuccess
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results
from stackops.secrets.readers import VirusTotalApiKey

if TYPE_CHECKING:
    import vt


class _Client:
    def __init__(self) -> None:
        self.closed = Event()

    def close(self) -> None:
        self.closed.set()


def test_file_api_failure_preserves_code_and_continues_remaining_files(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client()
    calls: list[Path] = []

    def create_client(api_key: str) -> "vt.Client":
        assert api_key == "dummy-key"
        return cast("vt.Client", client)

    def scan_file(path: Path, client: "vt.Client", stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert stop is not None and request_lock is not None
        calls.append(path)
        if path.name == "failed.bin":
            return ScanFailure(stage="report lookup", error_type="APIError", error_code="QuotaExceededError")
        results: list[ScanResult] = [{"engine_name": "dummy-engine", "category": "undetected", "result": None}]
        return ScanSuccess(summary=summarize_scan_results(results), results=results, scanned_at=datetime.now(UTC), source="existing_report")

    monkeypatch.setattr(vt_workers, "get_vt_client", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    records = list(
        vt_workers.scan_files_with_vt(
            apps_to_scan=[(Path("failed.bin"), None), (Path("ok.bin"), None)],
            credentials=(VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),),
            apps_per_key=1,
        )
    )

    assert calls == [Path("failed.bin"), Path("ok.bin")]
    assert len(records) == 2
    assert isinstance(records[0].outcome, ScanFailure)
    assert records[0].outcome.error_code == "QuotaExceededError"
    assert isinstance(records[1].outcome, ScanSuccess)
    assert client.closed.is_set()


def test_cancelled_work_cannot_finish_as_successful_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client()

    def create_client(api_key: str) -> "vt.Client":
        assert api_key == "dummy-key"
        return cast("vt.Client", client)

    def scan_file(path: Path, client: "vt.Client", stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert stop is not None and request_lock is not None
        stop.set()
        return ScanCancelled()

    monkeypatch.setattr(vt_workers, "get_vt_client", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    with pytest.raises(RuntimeError, match="stopped before all files"):
        list(
            vt_workers.scan_files_with_vt(
                apps_to_scan=[(Path("sample.bin"), None)],
                credentials=(VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),),
                apps_per_key=1,
            )
        )
    assert client.closed.wait(timeout=5)
