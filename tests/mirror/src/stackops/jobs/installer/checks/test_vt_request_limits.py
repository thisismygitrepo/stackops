import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from io import BytesIO
from threading import Event, Lock
from typing import cast

import pytest
import vt

from stackops.jobs.installer.checks import vt_requests
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_accounts import VtAccountPool
from stackops.jobs.installer.checks.vt_transport import VtTransport
from stackops.secrets.readers import VirusTotalApiKey


@dataclass
class _Clock:
    now: float

    def monotonic(self) -> float:
        return self.now

    def wait(self, seconds: float, stop: Event, deadline: float) -> None:
        assert not stop.is_set()
        self.now += max(0.0, seconds)
        assert self.now < deadline


def test_account_pacing_is_shared_across_workers_and_upload_phases(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = _Clock(time.monotonic())
    start = clock.now
    request_times: list[float] = []

    class RecordingTransport:
        def get_object(self, _path: str, _object_id: str, _deadline: float) -> vt.Object:
            request_times.append(clock.now)
            return vt.Object("file", "hash")

        def get_upload_url(self, _deadline: float) -> str:
            request_times.append(clock.now)
            return "https://upload-url"

        def upload_file(self, _upload_url: str, _file_bytes: bytes, _deadline: float) -> vt.Object:
            request_times.append(clock.now)
            return vt.Object("analysis", "id")

    monkeypatch.setattr(vt_requests, "time", clock)
    monkeypatch.setattr(vt_requests, "wait_for_request", clock.wait)
    monkeypatch.setattr(vt_requests, "VtTransport", lambda _api_key: cast(VtTransport, RecordingTransport()))
    stats = VirusTotalAccountStats(("account",))
    pool = VtAccountPool((VirusTotalApiKey("account", "private-key"),), stats)
    first = vt_requests.VtRequestClient(pool, 0, Event())
    second = vt_requests.VtRequestClient(pool, 0, Event())
    first.get_object("/files/{}", "first")
    second.get_object("/files/{}", "second")
    first.scan_file(BytesIO(b"payload"), wait_for_completion=False)
    assert request_times == [start, start + 15.0, start + 30.0, start + 45.0]
    assert stats.snapshots()[0].requests == 4


def test_two_workers_do_not_retry_an_account_disabled_by_other_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    bad_started = Event()
    release_bad = Event()
    record_lock = Lock()
    calls: dict[str, int] = {"inactive": 0, "healthy": 0}

    class RecordingTransport:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def get_object(self, _path: str, _object_id: str, _deadline: float) -> vt.Object:
            with record_lock:
                calls[self.api_key] += 1
            if self.api_key == "inactive":
                bad_started.set()
                assert release_bad.wait(timeout=5)
                raise vt.APIError("UserNotActiveError", "private")
            return vt.Object("file", "hash")

    monkeypatch.setattr(vt_requests, "VT_ACCOUNT_REQUEST_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(vt_requests, "VtTransport", lambda api_key: cast(VtTransport, RecordingTransport(api_key)))
    credentials = (VirusTotalApiKey("inactive-account", "inactive"), VirusTotalApiKey("healthy-account", "healthy"))
    stats = VirusTotalAccountStats(tuple(credential.account_name for credential in credentials))
    pool = VtAccountPool(credentials, stats)
    first = vt_requests.VtRequestClient(pool, 0, Event())
    second = vt_requests.VtRequestClient(pool, 0, Event())
    with ThreadPoolExecutor(max_workers=2) as executor:
        first_result = executor.submit(first.get_object, "/files/{}", "first")
        assert bad_started.wait(timeout=5)
        second_result = executor.submit(second.get_object, "/files/{}", "second")
        release_bad.set()
        assert first_result.result(timeout=5).id == "hash"
        assert second_result.result(timeout=5).id == "hash"
    assert calls == {"inactive": 1, "healthy": 2}
    assert stats.snapshots()[0].failed == 1


def test_cancellation_interrupts_account_pacing_before_request(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnusedTransport:
        def get_object(self, _path: str, _object_id: str, _deadline: float) -> vt.Object:
            pytest.fail("Cancellation must interrupt pacing before a request is sent.")

    monkeypatch.setattr(vt_requests, "VtTransport", lambda _api_key: cast(VtTransport, UnusedTransport()))
    stop = Event()
    stats = VirusTotalAccountStats(("account",))
    pool = VtAccountPool((VirusTotalApiKey("account", "private-key"),), stats)
    pool.accounts[0].next_request_at = time.monotonic() + 30.0
    client = vt_requests.VtRequestClient(pool, 0, stop)
    with ThreadPoolExecutor(max_workers=1) as executor:
        result = executor.submit(client.get_object, "/files/{}", "hash")
        stop.set()
        with pytest.raises(InterruptedError):
            result.result(timeout=5)
    assert stats.snapshots()[0].requests == 0


def test_deadline_interrupts_account_pacing_without_counting_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt_requests, "VtTransport", lambda _api_key: cast(VtTransport, object()))
    stats = VirusTotalAccountStats(("account",))
    pool = VtAccountPool((VirusTotalApiKey("account", "private-key"),), stats)
    pool.accounts[0].next_request_at = time.monotonic() + 30.0
    client = vt_requests.VtRequestClient(pool, 0, Event())
    client.set_request_context("report lookup", time.monotonic() + 0.01)
    with pytest.raises(TimeoutError):
        client.get_object("/files/{}", "hash")
    assert stats.snapshots()[0].requests == stats.snapshots()[0].failed == 0
