from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Lock
from typing import cast

import pytest

from stackops.jobs.installer.checks import vt_requests, vt_workers
from stackops.jobs.installer.checks.scan_outcomes import ScanCancelled, ScanFailure, ScanOutcome, ScanSuccess
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_accounts import VtAccountPool
from stackops.jobs.installer.checks.vt_requests import ScanClient, VtRequestClient
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results
from stackops.secrets.readers import VirusTotalApiKey

class _Client:
    def __init__(self) -> None:
        self.closed = Event()

    def close(self) -> None:
        self.closed.set()


def test_file_api_failure_preserves_code_and_continues_remaining_files(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client()
    calls: list[Path] = []

    def create_client(pool: VtAccountPool, preferred_account_index: int, stop: Event) -> VtRequestClient:
        assert pool is not None and preferred_account_index == 0 and not stop.is_set()
        return cast(VtRequestClient, client)

    def scan_file(path: Path, client: ScanClient, stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert stop is not None and request_lock is None
        calls.append(path)
        if path.name == "failed.bin":
            return ScanFailure(stage="report lookup", error_type="APIError", error_code="QuotaExceededError")
        results: list[ScanResult] = [{"engine_name": "dummy-engine", "category": "undetected", "result": None}]
        return ScanSuccess(summary=summarize_scan_results(results), results=results, scanned_at=datetime.now(UTC), source="existing_report")

    monkeypatch.setattr(vt_requests, "VtRequestClient", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    records = list(
        vt_workers.scan_files_with_vt(
            apps_to_scan=[(Path("failed.bin"), None), (Path("ok.bin"), None)],
            credentials=(VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),),
            concurrency=1,
            stats=VirusTotalAccountStats(("dummy-account",)),
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

    def create_client(pool: VtAccountPool, preferred_account_index: int, stop: Event) -> VtRequestClient:
        assert pool is not None and preferred_account_index == 0 and not stop.is_set()
        return cast(VtRequestClient, client)

    def scan_file(path: Path, client: ScanClient, stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert stop is not None and request_lock is None
        stop.set()
        return ScanCancelled()

    monkeypatch.setattr(vt_requests, "VtRequestClient", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    with pytest.raises(RuntimeError, match="stopped before all files"):
        list(
            vt_workers.scan_files_with_vt(
                apps_to_scan=[(Path("sample.bin"), None)],
                credentials=(VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),),
                concurrency=1,
                stats=VirusTotalAccountStats(("dummy-account",)),
            )
        )
    assert client.closed.wait(timeout=5)


def test_unexpected_failure_stops_queued_work_without_waiting_for_blocked_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    credentials = (
        VirusTotalApiKey(account_name="dummy-account-a", api_key="dummy-secret-a"),
        VirusTotalApiKey(account_name="dummy-account-b", api_key="dummy-secret-b"),
    )
    stats = VirusTotalAccountStats(tuple(credential.account_name for credential in credentials))
    scan_started = Event()
    release_scan = Event()
    lock = Lock()
    clients: list[_Client] = []
    paths_scanned: list[Path] = []

    def create_client(pool: VtAccountPool, preferred_account_index: int, stop: Event) -> VtRequestClient:
        assert pool is not None and preferred_account_index in (0, 1) and not stop.is_set()
        client = _Client()
        with lock:
            clients.append(client)
        return cast(VtRequestClient, client)

    def scan_file(path: Path, client: ScanClient, stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert stop is not None and request_lock is None
        with lock:
            paths_scanned.append(path)
        if path.name == "blocked.bin":
            scan_started.set()
            assert release_scan.wait(timeout=5)
            return ScanCancelled()
        assert scan_started.wait(timeout=5)
        raise ValueError("dummy-secret-b dummy-account-b")

    monkeypatch.setattr(vt_requests, "VtRequestClient", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    try:
        with pytest.raises(RuntimeError, match="VirusTotal file scan failed") as failure:
            list(
                vt_workers.scan_files_with_vt(
                    apps_to_scan=[(Path("blocked.bin"), None), (Path("failure.bin"), None), (Path("unstarted.bin"), None)],
                    credentials=credentials,
                    concurrency=2,
                    stats=stats,
                )
            )
        assert "dummy-secret" not in str(failure.value)
        assert "dummy-account" not in str(failure.value)
        assert not release_scan.is_set()
    finally:
        release_scan.set()
        assert all(client.closed.wait(timeout=5) for client in clients)
    assert set(paths_scanned) == {Path("blocked.bin"), Path("failure.bin")}
