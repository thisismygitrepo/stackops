from asyncio import AbstractEventLoop, get_event_loop
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, UTC
from pathlib import Path
from threading import Barrier, Event, Lock, get_ident
from typing import TYPE_CHECKING, cast

import pytest

from stackops.jobs.installer.checks import vt_workers
from stackops.jobs.installer.checks.scan_outcomes import ScanCancelled, ScanFailure, ScanOutcome, ScanSuccess
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results
from stackops.secrets.readers import VirusTotalApiKey

if TYPE_CHECKING:
    import vt


@dataclass
class _RecordedClient:
    api_key: str
    created_thread: int
    closed_thread: int | None = None
    closed: Event = field(default_factory=Event)

    def close(self) -> None:
        self.closed_thread = get_ident()
        self.closed.set()


@pytest.mark.parametrize(("apps_per_key", "distinct_apps"), [(1, 9), (2, 9), (2, 3), (2, 1)])
def test_scans_overlap_per_key_and_preserve_file_identity(apps_per_key: int, distinct_apps: int, monkeypatch: pytest.MonkeyPatch) -> None:
    credentials = tuple(VirusTotalApiKey(account_name=f"""account-{index}""", api_key=f"""dummy-{index}""") for index in range(3))
    apps = [(Path(f"""sample-{index}.bin"""), str(index)) for index in range(distinct_apps)]
    apps.append((apps[0][0], "duplicate-path"))
    worker_count = min(len(apps), len(credentials) * apps_per_key)
    barrier = Barrier(worker_count)
    lock = Lock()
    clients: list[_RecordedClient] = []
    event_loops: list[AbstractEventLoop] = []
    active: Counter[str] = Counter()
    maximum_per_key: Counter[str] = Counter()
    calls: list[Path] = []
    started_clients: set[int] = set()
    request_locks: dict[str, Lock] = {}
    active_requests: Counter[str] = Counter()
    maximum_requests_per_key: Counter[str] = Counter()
    peak_parallel = 0

    def create_client(api_key: str) -> "vt.Client":
        client = _RecordedClient(api_key=api_key, created_thread=get_ident())
        with lock:
            clients.append(client)
            event_loops.append(get_event_loop())
        return cast("vt.Client", client)

    def scan_file(
        path: Path, client: "vt.Client", stop: Event | None, request_lock: Lock | None
    ) -> ScanOutcome:
        nonlocal peak_parallel
        assert stop is not None
        assert request_lock is not None
        recorded_client = cast(_RecordedClient, client)
        with lock:
            active[recorded_client.api_key] += 1
            maximum_per_key[recorded_client.api_key] = max(maximum_per_key[recorded_client.api_key], active[recorded_client.api_key])
            peak_parallel = max(peak_parallel, sum(active.values()))
            first_scan = recorded_client.created_thread not in started_clients
            started_clients.add(recorded_client.created_thread)
            previous_request_lock = request_locks.setdefault(recorded_client.api_key, request_lock)
            assert previous_request_lock is request_lock
            calls.append(path)
        try:
            if first_scan:
                barrier.wait(timeout=5)
            for _request in range(2):
                with request_lock:
                    with lock:
                        active_requests[recorded_client.api_key] += 1
                        maximum_requests_per_key[recorded_client.api_key] = max(
                            maximum_requests_per_key[recorded_client.api_key], active_requests[recorded_client.api_key]
                        )
                    Event().wait(timeout=0.001)
                    with lock:
                        active_requests[recorded_client.api_key] -= 1
            results: list[ScanResult] = [{"engine_name": path.name, "category": "undetected", "result": None}]
            return ScanSuccess(summary=summarize_scan_results(results), results=results, scanned_at=datetime.now(UTC), source="submitted_file")
        finally:
            with lock:
                active[recorded_client.api_key] -= 1

    monkeypatch.setattr(vt_workers, "get_vt_client", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)

    scanned = list(vt_workers.scan_files_with_vt(apps_to_scan=apps, credentials=credentials, apps_per_key=apps_per_key))

    assert peak_parallel == worker_count
    assert maximum_per_key == Counter(credentials[index % len(credentials)].api_key for index in range(worker_count))
    assert set(maximum_requests_per_key.values()) == {1}
    assert len({id(request_lock) for request_lock in request_locks.values()}) == min(worker_count, len(credentials))
    assert Counter(calls) == Counter(path for path, _version in apps)
    assert sorted(result.index for result in scanned) == list(range(len(apps)))
    for result in scanned:
        assert (result.path, result.version) == apps[result.index]
        assert isinstance(result.outcome, ScanSuccess)
        assert result.outcome.results[0]["engine_name"] == result.path.name
    assert {client.api_key for client in clients} == {credential.api_key for credential in credentials[:worker_count]}
    assert all(client.closed.is_set() and client.closed_thread == client.created_thread != get_ident() for client in clients)
    assert len(event_loops) == worker_count and all(loop.is_closed() for loop in event_loops)


def test_scan_failure_is_prompt_and_in_flight_clients_close(monkeypatch: pytest.MonkeyPatch) -> None:
    credentials = (
        VirusTotalApiKey(account_name="dummy-account-a", api_key="dummy-secret-a"),
        VirusTotalApiKey(account_name="dummy-account-b", api_key="dummy-secret-b"),
    )
    apps = [(Path("blocked.bin"), None), (Path("failure.bin"), None), (Path("unstarted.bin"), None)]
    scan_started = Event()
    release_scan = Event()
    clients: list[_RecordedClient] = []
    paths_scanned: list[Path] = []
    lock = Lock()

    def create_client(api_key: str) -> "vt.Client":
        client = _RecordedClient(api_key=api_key, created_thread=get_ident())
        with lock:
            clients.append(client)
        return cast("vt.Client", client)

    def scan_file(
        path: Path, client: "vt.Client", stop: Event | None, request_lock: Lock | None
    ) -> ScanOutcome:
        assert stop is not None
        assert request_lock is not None
        with lock:
            paths_scanned.append(path)
        if path.name == "blocked.bin":
            scan_started.set()
            assert release_scan.wait(timeout=5)
            return ScanCancelled()
        assert scan_started.wait(timeout=5)
        recorded_client = cast(_RecordedClient, client)
        raise ValueError(f"""{recorded_client.api_key} dummy-account-b""")

    monkeypatch.setattr(vt_workers, "get_vt_client", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)

    try:
        with pytest.raises(RuntimeError, match="VirusTotal file scan failed") as failure:
            list(vt_workers.scan_files_with_vt(apps_to_scan=apps, credentials=credentials, apps_per_key=1))
        assert "dummy-secret" not in str(failure.value)
        assert "dummy-account" not in str(failure.value)
        assert not release_scan.is_set()
    finally:
        release_scan.set()
        assert all(client.closed.wait(timeout=5) for client in clients)
    assert set(paths_scanned) == {Path("blocked.bin"), Path("failure.bin")}
    assert all(client.closed_thread == client.created_thread for client in clients)


@pytest.mark.parametrize("stage", ["client creation", "client closure"])
def test_client_lifecycle_failures_are_reported_without_credentials(stage: str, monkeypatch: pytest.MonkeyPatch) -> None:
    credential = VirusTotalApiKey(account_name="dummy-account", api_key="dummy-secret")
    client = _RecordedClient(api_key=credential.api_key, created_thread=0)

    def create_client(api_key: str) -> "vt.Client":
        if stage == "client creation":
            raise ValueError(f"""{api_key} {credential.account_name}""")
        client.created_thread = get_ident()
        return cast("vt.Client", client)

    def close_client(recorded_client: _RecordedClient) -> None:
        recorded_client.closed_thread = get_ident()
        recorded_client.closed.set()
        raise ValueError(f"""{recorded_client.api_key} {credential.account_name}""")

    def scan_file(
        path: Path, client: "vt.Client", stop: Event | None, request_lock: Lock | None
    ) -> ScanOutcome:
        assert path == Path("sample.bin")
        assert cast(_RecordedClient, client).api_key == credential.api_key
        assert stop is not None
        assert request_lock is not None
        return ScanFailure(stage="report lookup", error_type="APIError", error_code="ForbiddenError")

    monkeypatch.setattr(vt_workers, "get_vt_client", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    monkeypatch.setattr(_RecordedClient, "close", close_client)

    with pytest.raises(RuntimeError, match=f"""VirusTotal {stage} failed""") as failure:
        list(vt_workers.scan_files_with_vt(apps_to_scan=[(Path("sample.bin"), None)], credentials=(credential,), apps_per_key=1))
    assert credential.api_key not in str(failure.value)
    assert credential.account_name not in str(failure.value)
    if stage == "client closure":
        assert client.closed.wait(timeout=5)
        assert client.closed_thread == client.created_thread


def test_closing_iterator_stops_pending_work_and_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    credential = VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key")
    client = _RecordedClient(api_key=credential.api_key, created_thread=0)
    waiting = Event()
    scanned_paths: list[Path] = []

    def create_client(api_key: str) -> "vt.Client":
        assert api_key == credential.api_key
        client.created_thread = get_ident()
        return cast("vt.Client", client)

    def scan_file(
        path: Path, client: "vt.Client", stop: Event | None, request_lock: Lock | None
    ) -> ScanOutcome:
        assert stop is not None
        assert request_lock is not None
        assert cast(_RecordedClient, client).api_key == credential.api_key
        scanned_paths.append(path)
        if len(scanned_paths) == 2:
            waiting.set()
            assert stop.wait(timeout=5)
            return ScanCancelled()
        results: list[ScanResult] = [{"engine_name": "dummy-engine", "category": "undetected", "result": None}]
        return ScanSuccess(summary=summarize_scan_results(results), results=results, scanned_at=datetime.now(UTC), source="submitted_file")

    monkeypatch.setattr(vt_workers, "get_vt_client", create_client)
    monkeypatch.setattr(vt_workers, "scan_file", scan_file)
    iterator = vt_workers.scan_files_with_vt(apps_to_scan=[(Path(str(index)), None) for index in range(3)], credentials=(credential,), apps_per_key=1)
    assert next(iterator).index == 0
    assert waiting.wait(timeout=5)
    iterator.close()
    assert client.closed.wait(timeout=5)
    assert scanned_paths == [Path("0"), Path("1")]


@pytest.mark.parametrize("apps_per_key", [0, -1])
def test_nonpositive_apps_per_key_is_rejected(apps_per_key: int, monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_client(api_key: str) -> "vt.Client":
        assert api_key == "dummy-key"
        pytest.fail("Invalid concurrency must not create clients.")

    monkeypatch.setattr(vt_workers, "get_vt_client", unexpected_client)
    with pytest.raises(ValueError, match="at least one"):
        list(
            vt_workers.scan_files_with_vt(
                apps_to_scan=[(Path("sample.bin"), None)],
                credentials=(VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),),
                apps_per_key=apps_per_key,
            )
        )
