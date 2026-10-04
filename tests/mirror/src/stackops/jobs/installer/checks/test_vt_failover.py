from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import Event
from typing import cast

import pytest
import vt

from stackops.jobs.installer.checks import vt_request_errors, vt_requests, vt_scanner
from stackops.jobs.installer.checks.scan_outcomes import ScanFailure, ScanSuccess
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_accounts import VtAccountPool
from stackops.jobs.installer.checks.vt_requests import VtRequestClient
from stackops.jobs.installer.checks.vt_transport import VtTransport
from stackops.secrets.readers import VirusTotalApiKey

FILE_BYTES = b"dummy-file"
FILE_HASH = sha256(FILE_BYTES).hexdigest()
SCAN_DATE = datetime(2026, 10, 4, 1, 2, tzinfo=UTC)
type _Script = list[tuple[str, str, vt.Object | str | Exception]]


@dataclass
class _ScriptedTransport:
    script: _Script
    requests: list[tuple[str, str]] = field(default_factory=list)
    closed: bool = False

    def _consume(self, operation: str, object_id: str) -> vt.Object | str:
        self.requests.append((operation, object_id))
        expected_operation, expected_id, response = self.script.pop(0)
        assert (operation, object_id) == (expected_operation, expected_id)
        if isinstance(response, Exception):
            raise response
        return response

    def get_object(self, path: str, object_id: str, deadline: float) -> vt.Object:
        assert deadline > 0.0
        response = self._consume(path, object_id)
        assert isinstance(response, vt.Object)
        return response

    def get_upload_url(self, deadline: float) -> str:
        assert deadline > 0.0
        response = self._consume("upload URL", "")
        assert isinstance(response, str)
        return response

    def upload_file(self, upload_url: str, file_bytes: bytes, deadline: float) -> vt.Object:
        assert deadline > 0.0
        assert file_bytes == FILE_BYTES
        response = self._consume("upload", upload_url)
        assert isinstance(response, vt.Object)
        return response

    def close(self) -> None:
        self.closed = True


def _make_proxy(scripts: dict[str, _Script], monkeypatch: pytest.MonkeyPatch) -> tuple[VtRequestClient, VirusTotalAccountStats, dict[str, _ScriptedTransport]]:
    credentials = tuple(VirusTotalApiKey(account_name=name, api_key=f"""dummy-secret-{name}""") for name in scripts)
    stats = VirusTotalAccountStats(tuple(scripts))
    transports = {name: _ScriptedTransport(script) for name, script in scripts.items()}
    key_accounts = {credential.api_key: credential.account_name for credential in credentials}

    def create_transport(api_key: str) -> VtTransport:
        return cast(VtTransport, transports[key_accounts[api_key]])

    monkeypatch.setattr(vt_requests, "VtTransport", create_transport)
    monkeypatch.setattr(vt_requests, "VT_ACCOUNT_REQUEST_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(vt_request_errors, "VT_RETRY_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(vt_request_errors, "VT_QUOTA_RETRY_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(vt_scanner, "VT_POLL_INTERVAL_SECONDS", 0.0)
    pool = VtAccountPool(credentials=credentials, stats=stats)
    client = VtRequestClient(pool=pool, preferred_account_index=0, stop=Event())
    return client, stats, transports


def test_real_scanner_recovers_same_file_and_never_reuses_inactive_account(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "sample"
    path.write_bytes(FILE_BYTES)
    report = vt.Object("file", FILE_HASH, {"last_analysis_results": {"A": {"category": "undetected", "result": None}}, "last_analysis_date": SCAN_DATE})
    client, stats, transports = _make_proxy(
        {
            "inactive": [("/files/{}", FILE_HASH, vt.APIError("UserNotActiveError", "dummy-secret-inactive"))],
            "healthy": [("/files/{}", FILE_HASH, report), ("/files/{}", FILE_HASH, report)],
        },
        monkeypatch,
    )
    try:
        first = vt_scanner.scan_file(path, client, stop=None, request_lock=None)
        second = vt_scanner.scan_file(path, client, stop=None, request_lock=None)
    finally:
        client.close()

    assert isinstance(first, ScanSuccess) and isinstance(second, ScanSuccess)
    assert first.source == second.source == "existing_report"
    inactive, healthy = stats.snapshots()
    assert (inactive.requests, inactive.failed, inactive.retries, inactive.failovers) == (1, 1, 0, 1)
    assert inactive.disabled_reason == "UserNotActiveError"
    assert healthy.requests == healthy.succeeded == 2
    assert all(not transport.script and transport.closed for transport in transports.values())
    assert "dummy-secret" not in repr(stats.snapshots())


@pytest.mark.parametrize("error_code", ["QuotaExceededError", "TransientError"])
def test_polling_failover_keeps_uploaded_analysis_id_and_never_reuploads(error_code: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "sample"
    path.write_bytes(FILE_BYTES)
    upload_url = "https://www.virustotal.com/upload/one-time"
    completed = vt.Object("analysis", "analysis-id", {"status": "completed", "results": {"A": {"category": "undetected", "result": None}}, "date": SCAN_DATE})
    client, stats, transports = _make_proxy(
        {
            "failing": [
                ("/files/{}", FILE_HASH, vt.APIError("NotFoundError", "missing")),
                ("upload URL", "", upload_url),
                ("upload", upload_url, vt.Object("analysis", "analysis-id")),
                *[("/analyses/{}", "analysis-id", vt.APIError(error_code, "private account details")) for _attempt in range(3)],
            ],
            "healthy": [("/analyses/{}", "analysis-id", completed)],
        },
        monkeypatch,
    )
    try:
        result = vt_scanner.scan_file(path, client, stop=None, request_lock=None)
    finally:
        client.close()

    assert isinstance(result, ScanSuccess)
    assert result.source == "submitted_file" and result.scanned_at == SCAN_DATE
    failing, healthy = stats.snapshots()
    assert (failing.requests, failing.succeeded, failing.expected, failing.failed, failing.retries, failing.failovers) == (6, 2, 1, 3, 2, 1)
    assert failing.disabled_reason == error_code
    assert healthy.requests == healthy.succeeded == 1
    assert [request for transport in transports.values() for request in transport.requests if request[0] == "upload"] == [("upload", upload_url)]
    assert all(not transport.script and transport.closed for transport in transports.values())


def test_all_disabled_accounts_fail_next_file_without_sending_more_requests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "sample"
    path.write_bytes(FILE_BYTES)
    client, stats, transports = _make_proxy(
        {name: [("/files/{}", FILE_HASH, vt.APIError("UserNotActiveError", "private account details"))] for name in ("first", "second")},
        monkeypatch,
    )
    try:
        first = vt_scanner.scan_file(path, client, stop=None, request_lock=None)
        second = vt_scanner.scan_file(path, client, stop=None, request_lock=None)
    finally:
        client.close()

    assert isinstance(first, ScanFailure) and first.error_code == "UserNotActiveError"
    assert isinstance(second, ScanFailure) and second.error_type == "AccountsUnavailableError"
    assert sum(account.requests for account in stats.snapshots()) == 2
    assert all(account.disabled_reason == "UserNotActiveError" for account in stats.snapshots())
    assert all(not transport.script and transport.closed for transport in transports.values())
