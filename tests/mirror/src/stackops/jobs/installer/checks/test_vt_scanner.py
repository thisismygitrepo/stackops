from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Event
from typing import cast

import pytest
import vt

from stackops.jobs.installer.checks import vt_scanner
from stackops.jobs.installer.checks.scan_outcomes import ScanCancelled, ScanFailure, ScanSuccess, format_scan_failure

FILE_BYTES = b"dummy-file"
FILE_HASH = sha256(FILE_BYTES).hexdigest()
SCAN_DATE = datetime(2025, 2, 3, 4, 5, tzinfo=UTC)


class _ScriptedClient:
    def __init__(self, script: list[tuple[str, str, vt.Object | Exception]]) -> None:
        self.script = script
        self.requests: list[tuple[str, str]] = []

    def _consume(self, operation: str, object_id: str) -> vt.Object:
        self.requests.append((operation, object_id))
        expected_operation, expected_id, response = self.script.pop(0)
        assert (operation, object_id) == (expected_operation, expected_id)
        if isinstance(response, Exception):
            raise response
        return response

    def get_object(self, path: str, object_id: str) -> vt.Object:
        return self._consume(path, object_id)

    def scan_file(self, file: BytesIO, wait_for_completion: bool) -> vt.Object:
        assert file.read() == FILE_BYTES
        assert wait_for_completion is False
        return self._consume("upload", FILE_HASH)


@pytest.fixture
def sample_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample"
    path.write_bytes(FILE_BYTES)
    return path


@pytest.fixture
def file_report() -> vt.Object:
    return vt.Object("file", FILE_HASH, {"last_analysis_results": {"A": {"category": "undetected", "result": None}}, "last_analysis_date": SCAN_DATE})


def test_known_hash_reuses_report_without_upload(sample_path: Path, file_report: vt.Object) -> None:
    client = _ScriptedClient([("/files/{}", FILE_HASH, file_report)])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert isinstance(result, ScanSuccess)
    assert result.summary["verdict_engines"] == 1
    assert result.source == "existing_report"
    assert result.scanned_at == SCAN_DATE
    assert client.requests == [("/files/{}", FILE_HASH)]


def test_not_found_uploads_then_polls_completed_analysis(sample_path: Path) -> None:
    completed = vt.Object("analysis", "analysis-id", {"status": "completed", "results": {}, "date": SCAN_DATE})
    client = _ScriptedClient([
        ("/files/{}", FILE_HASH, vt.APIError("NotFoundError", "missing")),
        ("upload", FILE_HASH, vt.Object("analysis", "analysis-id")),
        ("/analyses/{}", "analysis-id", completed),
    ])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert isinstance(result, ScanSuccess)
    assert result.source == "submitted_file"
    assert result.scanned_at == SCAN_DATE
    assert result.summary["verdict_engines"] == 0
    assert result.summary["notes"] == "VirusTotal returned no engine results."
    assert not client.script


def test_duplicate_upload_race_waits_for_existing_report(sample_path: Path, file_report: vt.Object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt_scanner, "VT_POLL_INTERVAL_SECONDS", 0.0)
    client = _ScriptedClient([
        ("/files/{}", FILE_HASH, vt.APIError("NotFoundError", "missing")),
        ("upload", FILE_HASH, vt.APIError("AlreadySubmittedError", "already submitted")),
        ("/files/{}", FILE_HASH, vt.APIError("NotFoundError", "not propagated")),
        ("/files/{}", FILE_HASH, vt.APIError("NotAvailableYet", "pending")),
        ("/files/{}", FILE_HASH, file_report),
    ])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert isinstance(result, ScanSuccess)
    assert result.source == "existing_report"
    assert not client.script


@pytest.mark.parametrize("error_code", ["WrongCredentialsError", "QuotaExceededError", "ForbiddenError", "TransientError", "BadRequestError"])
def test_lookup_errors_fail_without_upload_or_retry(sample_path: Path, error_code: str) -> None:
    client = _ScriptedClient([("/files/{}", FILE_HASH, vt.APIError(error_code, "secret-key account details"))])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert result == ScanFailure(stage="report lookup", error_type="APIError", error_code=error_code)
    assert "secret-key" not in format_scan_failure(result)
    assert len(client.requests) == 1


def test_pending_existing_report_polls_without_upload(sample_path: Path, file_report: vt.Object, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt_scanner, "VT_POLL_INTERVAL_SECONDS", 0.0)
    client = _ScriptedClient([
        ("/files/{}", FILE_HASH, vt.Object("file", FILE_HASH, {"last_analysis_results": {}})),
        ("/files/{}", FILE_HASH, vt.APIError("NotAvailableYet", "pending")),
        ("/files/{}", FILE_HASH, file_report),
    ])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert isinstance(result, ScanSuccess)
    assert not client.script


def test_pending_deadline_returns_timeout(sample_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vt_scanner, "VT_ANALYSIS_TIMEOUT_SECONDS", 0.0)
    client = _ScriptedClient([("/files/{}", FILE_HASH, vt.Object("file", FILE_HASH, {"last_analysis_results": {}}))])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert result == ScanFailure(stage="analysis polling", error_type="TimeoutError", error_code=None)
    assert len(client.requests) == 1


def test_cancelled_scan_never_reads_file_or_sends_requests() -> None:
    stop = Event()
    stop.set()
    client = _ScriptedClient([])

    result = vt_scanner.scan_file(Path("missing-dummy-file"), cast(vt.Client, client), stop=stop, request_lock=None)

    assert isinstance(result, ScanCancelled)
    assert not client.requests


def test_cancellation_interrupts_pending_response(sample_path: Path) -> None:
    stop = Event()

    class _CancellingClient(_ScriptedClient):
        def get_object(self, path: str, object_id: str) -> vt.Object:
            response = super().get_object(path, object_id)
            stop.set()
            return response

    client = _CancellingClient([("/files/{}", FILE_HASH, vt.Object("file", FILE_HASH, {"last_analysis_results": {}}))])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=stop, request_lock=None)

    assert isinstance(result, ScanCancelled)
    assert len(client.requests) == 1


@pytest.mark.parametrize("attributes", [{"last_analysis_results": []}, {"last_analysis_results": {"A": {"category": "undetected"}}}])
def test_invalid_report_shape_or_missing_date_is_explicit_failure(sample_path: Path, attributes: dict[str, object]) -> None:
    client = _ScriptedClient([("/files/{}", FILE_HASH, vt.Object("file", FILE_HASH, attributes))])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert result == ScanFailure(stage="result parsing", error_type="ValueError", error_code=None)


@pytest.mark.parametrize(
    ("upload_response", "poll_response", "failure"),
    [
        (vt.APIError("QuotaExceededError", "private details"), None, ScanFailure("file upload", "APIError", "QuotaExceededError")),
        (vt.Object("analysis", "analysis-id"), vt.APIError("QuotaExceededError", "private details"), ScanFailure("analysis polling", "APIError", "QuotaExceededError")),
        (vt.Object("analysis", "analysis-id"), vt.APIError("NotFoundError", "missing"), ScanFailure("analysis polling", "APIError", "NotFoundError")),
        (vt.Object("analysis", None), None, ScanFailure("result parsing", "ValueError", None)),
        (vt.Object("analysis", "analysis-id"), vt.Object("analysis", "analysis-id", {"status": "unknown"}), ScanFailure("result parsing", "ValueError", None)),
        (vt.Object("analysis", "analysis-id"), vt.Object("analysis", "analysis-id", {"status": "completed", "results": []}), ScanFailure("result parsing", "ValueError", None)),
    ],
)
def test_upload_and_poll_failures_are_explicit_and_not_retried(sample_path: Path, upload_response: vt.Object | Exception, poll_response: vt.Object | Exception | None, failure: ScanFailure) -> None:
    script: list[tuple[str, str, vt.Object | Exception]] = [("/files/{}", FILE_HASH, vt.APIError("NotFoundError", "missing")), ("upload", FILE_HASH, upload_response)]
    if poll_response is not None:
        script.append(("/analyses/{}", "analysis-id", poll_response))
    client = _ScriptedClient(script)

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert result == failure
    assert not client.script


def test_upload_uses_the_exact_bytes_from_hash_lookup(sample_path: Path) -> None:
    class _ChangingFileClient(_ScriptedClient):
        def get_object(self, path: str, object_id: str) -> vt.Object:
            sample_path.write_bytes(b"changed-after-hash")
            return super().get_object(path, object_id)

    client = _ChangingFileClient([
        ("/files/{}", FILE_HASH, vt.APIError("NotFoundError", "missing")),
        ("upload", FILE_HASH, vt.APIError("QuotaExceededError", "quota")),
    ])

    result = vt_scanner.scan_file(sample_path, cast(vt.Client, client), stop=None, request_lock=None)

    assert result == ScanFailure("file upload", "APIError", "QuotaExceededError")
