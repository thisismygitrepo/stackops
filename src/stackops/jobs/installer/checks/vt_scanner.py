import time
from contextlib import nullcontext
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Event, Lock
from typing import TYPE_CHECKING, assert_never

from stackops.jobs.installer.checks.constants import VT_ANALYSIS_TIMEOUT_SECONDS, VT_POLL_INTERVAL_SECONDS
from stackops.jobs.installer.checks.scan_outcomes import ScanCancelled, ScanFailure, ScanOutcome, ScanSource, ScanStage, ScanSuccess
from stackops.jobs.installer.checks.vt_utils import normalize_scan_results, summarize_scan_results

if TYPE_CHECKING:
    import vt
    from stackops.jobs.installer.checks.vt_requests import ScanClient


def _completed_report(response: "vt.Object", source: ScanSource) -> ScanSuccess | None:
    if source == "existing_report":
        raw_results: object = getattr(response, "last_analysis_results", None)
        if raw_results is None:
            return None
        results = normalize_scan_results(raw_results)
        if not results:
            return None
        scanned_at: object = getattr(response, "last_analysis_date", None)
    elif source == "submitted_file":
        status: object = getattr(response, "status", None)
        if status in ("queued", "in-progress"):
            return None
        if status != "completed":
            raise ValueError("VirusTotal returned an invalid analysis status.")
        results = normalize_scan_results(getattr(response, "results", None))
        scanned_at = getattr(response, "date", None)
    else:
        assert_never(source)
    if not isinstance(scanned_at, datetime) or scanned_at.tzinfo is None:
        raise ValueError("VirusTotal returned an invalid analysis timestamp.")
    return ScanSuccess(summary=summarize_scan_results(results), results=results, scanned_at=scanned_at.astimezone(UTC), source=source)


def _poll_results(
    client: "ScanClient",
    object_id: str,
    source: ScanSource,
    initial_response: "vt.Object | None",
    stop: Event | None,
    request_lock: Lock | None,
    deadline: float,
    pending_not_found: bool,
) -> ScanOutcome:
    import aiohttp
    import vt
    from stackops.jobs.installer.checks.vt_requests import VtRequestClient

    response = initial_response
    endpoint = "/files/{}" if source == "existing_report" else "/analyses/{}"
    while True:
        if stop is not None and stop.is_set():
            return ScanCancelled()
        if time.monotonic() >= deadline:
            return ScanFailure(stage="analysis polling", error_type="TimeoutError", error_code=None)
        stage: ScanStage = "analysis polling"
        try:
            if response is None:
                if isinstance(client, VtRequestClient):
                    client.set_request_context(stage=stage, deadline=deadline)
                with request_lock if request_lock is not None else nullcontext():
                    if stop is not None and stop.is_set():
                        return ScanCancelled()
                    response = client.get_object(endpoint, object_id)
            if stop is not None and stop.is_set():
                return ScanCancelled()
            stage = "result parsing"
            completed = _completed_report(response, source)
            if completed is not None:
                return completed
        except vt.APIError as exc:
            if exc.code != "NotAvailableYet" and not (pending_not_found and exc.code == "NotFoundError"):
                return ScanFailure(stage=stage, error_type=type(exc).__name__, error_code=exc.code)
        except (OSError, ValueError, TypeError, AttributeError, OverflowError, aiohttp.ClientError) as exc:
            if stop is not None and stop.is_set():
                return ScanCancelled()
            return ScanFailure(stage=stage, error_type=type(exc).__name__, error_code=None)
        response = None
        wait_seconds = min(VT_POLL_INTERVAL_SECONDS, max(0.0, deadline - time.monotonic()))
        if stop is None:
            time.sleep(wait_seconds)
        elif stop.wait(wait_seconds):
            return ScanCancelled()


def scan_file(path: Path, client: "ScanClient", stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
    if stop is not None and stop.is_set():
        return ScanCancelled()
    import aiohttp
    import vt
    from stackops.jobs.installer.checks.vt_requests import VtRequestClient

    stage: ScanStage = "file read"
    try:
        file_bytes = path.read_bytes()
        file_hash = sha256(file_bytes).hexdigest()
        deadline = time.monotonic() + VT_ANALYSIS_TIMEOUT_SECONDS
        stage = "report lookup"
        try:
            if isinstance(client, VtRequestClient):
                client.set_request_context(stage=stage, deadline=deadline)
            with request_lock if request_lock is not None else nullcontext():
                if stop is not None and stop.is_set():
                    return ScanCancelled()
                report = client.get_object("/files/{}", file_hash)
        except vt.APIError as exc:
            if exc.code == "NotAvailableYet":
                return _poll_results(client, file_hash, "existing_report", None, stop, request_lock, deadline, pending_not_found=False)
            if exc.code != "NotFoundError":
                raise
        else:
            return _poll_results(client, file_hash, "existing_report", report, stop, request_lock, deadline, pending_not_found=False)

        stage = "file upload"
        try:
            if isinstance(client, VtRequestClient):
                client.set_request_context(stage=stage, deadline=deadline)
            with BytesIO(file_bytes) as file_handle, request_lock if request_lock is not None else nullcontext():
                if stop is not None and stop.is_set():
                    return ScanCancelled()
                analysis = client.scan_file(file_handle, wait_for_completion=False)
        except vt.APIError as exc:
            if exc.code != "AlreadySubmittedError":
                raise
            return _poll_results(client, file_hash, "existing_report", None, stop, request_lock, deadline, pending_not_found=True)
        stage = "result parsing"
        analysis_id: object = analysis.id
        if not isinstance(analysis_id, str) or not analysis_id:
            raise ValueError("VirusTotal upload returned no analysis ID.")
        return _poll_results(client, analysis_id, "submitted_file", None, stop, request_lock, deadline, pending_not_found=False)
    except vt.APIError as exc:
        return ScanFailure(stage=stage, error_type=type(exc).__name__, error_code=exc.code)
    except (OSError, ValueError, TypeError, AttributeError, OverflowError, aiohttp.ClientError) as exc:
        if stop is not None and stop.is_set():
            return ScanCancelled()
        return ScanFailure(stage=stage, error_type=type(exc).__name__, error_code=None)
