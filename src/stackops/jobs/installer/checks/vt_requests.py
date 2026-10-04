import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event
from typing import BinaryIO, Protocol, assert_never

import vt

from stackops.jobs.installer.checks.constants import VT_ACCOUNT_REQUEST_INTERVAL_SECONDS, VT_ANALYSIS_TIMEOUT_SECONDS, VT_REQUEST_ATTEMPTS_PER_ACCOUNT
from stackops.jobs.installer.checks.scan_outcomes import ScanStage
from stackops.jobs.installer.checks.vt_accounts import AccountsUnavailableError, VtAccountPool, acquire_request_lock, wait_for_request
from stackops.jobs.installer.checks.vt_request_errors import classify_request_error
from stackops.jobs.installer.checks.vt_transport import VtTransport


@dataclass(frozen=True)
class _ReportLookup:
    path: str
    object_id: str


@dataclass(frozen=True)
class _FileUpload:
    file_bytes: bytes


type _Operation = _ReportLookup | _FileUpload


class ScanClient(Protocol):
    def get_object(self, path: str, object_id: str) -> vt.Object: ...

    def scan_file(self, file: BinaryIO, wait_for_completion: bool) -> vt.Object: ...


class VtRequestClient:
    def __init__(self, pool: VtAccountPool, preferred_account_index: int, stop: Event) -> None:
        self._pool = pool
        self._preferred_account_index = preferred_account_index
        self._stop = stop
        self._deadline = time.monotonic() + VT_ANALYSIS_TIMEOUT_SECONDS
        self._stage: ScanStage = "report lookup"
        self._transports = {preferred_account_index: VtTransport(pool.accounts[preferred_account_index].credential.api_key)}

    def set_request_context(self, stage: ScanStage, deadline: float) -> None:
        self._stage = stage
        self._deadline = deadline

    def get_object(self, path: str, object_id: str) -> vt.Object:
        return self._request(_ReportLookup(path, object_id))

    def scan_file(self, file: BinaryIO, wait_for_completion: bool) -> vt.Object:
        if wait_for_completion:
            raise ValueError("VirusTotal analysis polling must be handled by the scanner.")
        initial_position = file.tell()
        file_bytes = file.read()
        file.seek(initial_position)
        return self._request(_FileUpload(file_bytes))

    def close(self) -> None:
        first_error: Exception | None = None
        for transport in self._transports.values():
            try:
                transport.close()
            except Exception as error:
                if first_error is None:
                    first_error = error
        self._transports.clear()
        if first_error is not None:
            raise first_error

    def _send_single_request[T](self, account_index: int, operation: Callable[[], T], expected_codes: frozenset[str], is_retry: bool) -> T:
        account = self._pool.accounts[account_index]
        wait_for_request(account.next_request_at - time.monotonic(), self._stop, self._deadline)
        if is_retry:
            self._pool.stats.retried(account_index)
        self._pool.stats.request_started(account_index)
        account.next_request_at = time.monotonic() + VT_ACCOUNT_REQUEST_INTERVAL_SECONDS
        try:
            result = operation()
        except Exception as error:
            policy = classify_request_error(error)
            if policy.code in expected_codes:
                self._pool.stats.expected_response(account_index, policy.code)
            else:
                self._pool.stats.failed(account_index, self._stage, policy.code)
            raise policy.safe_error from None
        if isinstance(result, vt.Object) and getattr(result, "status", None) in ("queued", "in-progress"):
            self._pool.stats.expected_response(account_index, "AnalysisPending")
        else:
            self._pool.stats.succeeded(account_index)
        return result

    def _send_operation(self, account_index: int, transport: VtTransport, operation: _Operation, is_retry: bool) -> vt.Object:
        match operation:
            case _ReportLookup():
                expected_codes = frozenset({"NotAvailableYet", "NotFoundError"}) if operation.path == "/files/{}" else frozenset({"NotAvailableYet"})
                return self._send_single_request(
                    account_index, lambda: transport.get_object(operation.path, operation.object_id, self._deadline), expected_codes, is_retry
                )
            case _FileUpload():
                upload_url = self._send_single_request(account_index, lambda: transport.get_upload_url(self._deadline), frozenset(), is_retry)
                return self._send_single_request(
                    account_index,
                    lambda: transport.upload_file(upload_url, operation.file_bytes, self._deadline),
                    frozenset({"AlreadySubmittedError"}),
                    False,
                )
            case _:
                assert_never(operation)

    def _request(self, operation: _Operation) -> vt.Object:
        account_count = len(self._pool.accounts)
        last_error: Exception | None = None
        previous_account: int | None = None
        for offset in range(account_count):
            account_index = (self._preferred_account_index + offset) % account_count
            account = self._pool.accounts[account_index]
            acquire_request_lock(account, self._stop, self._deadline)
            try:
                if not account.available:
                    continue
                if previous_account is not None:
                    self._pool.stats.switched(previous_account, account_index)
                previous_account = account_index
                transport = self._transports.get(account_index)
                if transport is None:
                    transport = VtTransport(account.credential.api_key)
                    self._transports[account_index] = transport
                for attempt in range(VT_REQUEST_ATTEMPTS_PER_ACCOUNT):
                    try:
                        result = self._send_operation(account_index, transport, operation, attempt > 0)
                    except Exception as error:
                        policy = classify_request_error(error)
                        if policy.action == "expected":
                            self._preferred_account_index = account_index
                            raise policy.safe_error from None
                        last_error = policy.safe_error
                        match policy.action:
                            case "fail":
                                raise policy.safe_error from None
                            case "disable":
                                account.available = False
                                self._pool.stats.disabled(account_index, policy.code)
                                break
                            case "switch":
                                break
                            case "retry":
                                if attempt + 1 == VT_REQUEST_ATTEMPTS_PER_ACCOUNT:
                                    if policy.disable_after_exhaustion:
                                        account.available = False
                                        self._pool.stats.disabled(account_index, policy.code)
                                    break
                                wait_for_request(policy.retry_delay * 2**attempt, self._stop, self._deadline)
                            case _:
                                assert_never(policy.action)
                    else:
                        self._preferred_account_index = account_index
                        return result
            finally:
                account.request_lock.release()
        if last_error is not None:
            raise last_error from None
        raise AccountsUnavailableError("All configured VirusTotal accounts are unavailable for this scan.")
