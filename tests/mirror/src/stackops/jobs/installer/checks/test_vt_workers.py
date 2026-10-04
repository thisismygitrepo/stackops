from asyncio import AbstractEventLoop, get_event_loop
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Event, Lock, get_ident
from typing import cast

import pytest

from stackops.jobs.installer.checks import vt_requests, vt_workers
from stackops.jobs.installer.checks.scan_outcomes import ScanCancelled, ScanFailure, ScanOutcome, ScanSuccess
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_requests import ScanClient, VtAccountPool, VtRequestClient
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results
from stackops.secrets.readers import VirusTotalApiKey


@dataclass
class _RecordedClient:
    account_index: int
    created_thread: int
    closed_thread: int | None = None
    closed: Event = field(default_factory=Event)

    def close(self) -> None:
        self.closed_thread = get_ident()
        self.closed.set()


@pytest.mark.parametrize(("concurrency", "distinct_apps"), [(None, 9), (6, 9), (6, 3), (6, 1)])
def test_concurrent_files_preserve_identity_and_thread_owned_clients(
    concurrency: int | None, distinct_apps: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    credentials = tuple(VirusTotalApiKey(account_name=f"""account-{index}""", api_key=f"""dummy-{index}""") for index in range(3))
    apps = [(Path(f"""sample-{index}.bin"""), str(index)) for index in range(distinct_apps)]
    apps.append((apps[0][0], "duplicate-path"))
    worker_count = min(len(apps), len(credentials) if concurrency is None else concurrency)
    barrier = Barrier(worker_count)
    lock = Lock()
    clients: list[_RecordedClient] = []
    event_loops: list[AbstractEventLoop] = []
    calls: list[Path] = []
    started_threads: set[int] = set()
    pools: list[VtAccountPool] = []
    stats = VirusTotalAccountStats(tuple(credential.account_name for credential in credentials))

    def create_client(pool: VtAccountPool, preferred_account_index: int, stop: Event) -> VtRequestClient:
        assert not stop.is_set()
        client = _RecordedClient(account_index=preferred_account_index, created_thread=get_ident())
        with lock:
            clients.append(client)
            event_loops.append(get_event_loop())
            pools.append(pool)
        return cast(VtRequestClient, client)

    def scan_file(path: Path, client: ScanClient, stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert stop is not None and request_lock is None
        with lock:
            thread = cast(_RecordedClient, client).created_thread
            first_scan = thread not in started_threads
            started_threads.add(thread)
            calls.append(path)
        if first_scan:
            barrier.wait(timeout=5)
        results: list[ScanResult] = [{"engine_name": path.name, "category": "undetected", "result": None}]
        return ScanSuccess(summary=summarize_scan_results(results), results=results, scanned_at=datetime.now(UTC), source="existing_report")

    monkeypatch.setattr(vt_requests, "VtRequestClient", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    scanned = list(vt_workers.scan_files_with_vt(apps_to_scan=apps, credentials=credentials, concurrency=concurrency, stats=stats))

    assert len(clients) == worker_count
    assert len({id(pool) for pool in pools}) == 1
    assert Counter(calls) == Counter(path for path, _version in apps)
    assert sorted(result.index for result in scanned) == list(range(len(apps)))
    for result in scanned:
        assert (result.path, result.version) == apps[result.index]
        assert isinstance(result.outcome, ScanSuccess)
        assert result.outcome.results[0]["engine_name"] == result.path.name
    assert all(client.closed.is_set() and client.closed_thread == client.created_thread != get_ident() for client in clients)
    assert len(event_loops) == worker_count and all(loop.is_closed() for loop in event_loops)


@pytest.mark.parametrize("stage", ["client creation", "file scan", "client closure"])
def test_unexpected_worker_errors_never_expose_credentials(stage: str, monkeypatch: pytest.MonkeyPatch) -> None:
    credential = VirusTotalApiKey(account_name="dummy-account", api_key="dummy-secret")
    stats = VirusTotalAccountStats((credential.account_name,))
    client = _RecordedClient(account_index=0, created_thread=0)

    def create_client(pool: VtAccountPool, preferred_account_index: int, stop: Event) -> VtRequestClient:
        assert pool is not None and preferred_account_index == 0 and not stop.is_set()
        if stage == "client creation":
            raise ValueError(f"""{credential.api_key} {credential.account_name}""")
        client.created_thread = get_ident()
        return cast(VtRequestClient, client)

    def close_client(recorded_client: _RecordedClient) -> None:
        recorded_client.closed_thread = get_ident()
        recorded_client.closed.set()
        if stage == "client closure":
            raise ValueError(f"""{credential.api_key} {credential.account_name}""")

    def scan_file(path: Path, client: ScanClient, stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert path == Path("sample.bin") and stop is not None and request_lock is None
        if stage == "file scan":
            raise ValueError(f"""{credential.api_key} {credential.account_name}""")
        return ScanFailure(stage="report lookup", error_type="APIError", error_code="ForbiddenError")

    monkeypatch.setattr(vt_requests, "VtRequestClient", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    monkeypatch.setattr(_RecordedClient, "close", close_client)
    with pytest.raises(RuntimeError, match=f"""VirusTotal {stage} failed""") as failure:
        list(vt_workers.scan_files_with_vt(apps_to_scan=[(Path("sample.bin"), None)], credentials=(credential,), concurrency=1, stats=stats))
    assert credential.api_key not in str(failure.value)
    assert credential.account_name not in str(failure.value)
    if stage != "client creation":
        assert client.closed.wait(timeout=5)
        assert client.closed_thread == client.created_thread


def test_closing_iterator_stops_pending_work_and_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    credential = VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key")
    stats = VirusTotalAccountStats((credential.account_name,))
    client = _RecordedClient(account_index=0, created_thread=0)
    waiting = Event()
    scanned_paths: list[Path] = []

    def create_client(pool: VtAccountPool, preferred_account_index: int, stop: Event) -> VtRequestClient:
        assert pool is not None and preferred_account_index == 0 and not stop.is_set()
        client.created_thread = get_ident()
        return cast(VtRequestClient, client)

    def scan_file(path: Path, client: ScanClient, stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert stop is not None and request_lock is None
        scanned_paths.append(path)
        if len(scanned_paths) == 2:
            waiting.set()
            assert stop.wait(timeout=5)
            return ScanCancelled()
        results: list[ScanResult] = [{"engine_name": "dummy-engine", "category": "undetected", "result": None}]
        return ScanSuccess(summary=summarize_scan_results(results), results=results, scanned_at=datetime.now(UTC), source="existing_report")

    monkeypatch.setattr(vt_requests, "VtRequestClient", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    iterator = vt_workers.scan_files_with_vt(apps_to_scan=[(Path(str(index)), None) for index in range(3)], credentials=(credential,), concurrency=1, stats=stats)
    assert next(iterator).index == 0
    assert waiting.wait(timeout=5)
    iterator.close()
    assert client.closed.wait(timeout=5)
    assert scanned_paths == [Path("0"), Path("1")]


@pytest.mark.parametrize("concurrency", [0, -1])
def test_nonpositive_concurrency_is_rejected(concurrency: int) -> None:
    credential = VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key")
    stats = VirusTotalAccountStats((credential.account_name,))
    with pytest.raises(ValueError, match="at least one"):
        list(vt_workers.scan_files_with_vt(apps_to_scan=[(Path("sample.bin"), None)], credentials=(credential,), concurrency=concurrency, stats=stats))
