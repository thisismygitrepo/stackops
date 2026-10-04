import time
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from threading import Event
from typing import cast

import pytest
import vt

from stackops.jobs.installer.checks import vt_requests
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_accounts import AccountsUnavailableError, VtAccountPool
from stackops.jobs.installer.checks.vt_transport import VtTransport
from stackops.secrets.readers import VirusTotalApiKey

type Response = vt.Object | str | Exception
type Setup = tuple[vt_requests.VtRequestClient, VirusTotalAccountStats, list["_ScriptedTransport"]]
type ClientFactory = Callable[[list[list[Response]]], Setup]


@dataclass
class _ScriptedTransport:
    responses: list[Response]
    requests: list[tuple[str, str | bytes]]
    closed: bool

    def _consume(self, operation: str, argument: str | bytes) -> vt.Object | str:
        self.requests.append((operation, argument))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def get_object(self, path: str, object_id: str, _deadline: float) -> vt.Object:
        return cast(vt.Object, self._consume(path, object_id))

    def get_upload_url(self, _deadline: float) -> str:
        return cast(str, self._consume("upload URL", ""))

    def upload_file(self, upload_url: str, file_bytes: bytes, _deadline: float) -> vt.Object:
        return cast(vt.Object, self._consume(upload_url, file_bytes))

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def client_factory(monkeypatch: pytest.MonkeyPatch) -> ClientFactory:
    monkeypatch.setattr(vt_requests, "VT_ACCOUNT_REQUEST_INTERVAL_SECONDS", 0.0)
    monkeypatch.setattr(vt_requests, "wait_for_request", lambda _seconds, _stop, _deadline: None)

    def create(scripts: list[list[Response]]) -> Setup:
        credentials = tuple(VirusTotalApiKey(account_name=f"""account-{index}""", api_key=f"""secret-{index}""") for index in range(len(scripts)))
        transports = [_ScriptedTransport(script, [], False) for script in scripts]
        stats = VirusTotalAccountStats(tuple(credential.account_name for credential in credentials))

        def create_transport(api_key: str) -> VtTransport:
            index = next(index for index, credential in enumerate(credentials) if credential.api_key == api_key)
            return cast(VtTransport, transports[index])

        monkeypatch.setattr(vt_requests, "VtTransport", create_transport)
        client = vt_requests.VtRequestClient(VtAccountPool(credentials, stats), 0, Event())
        return client, stats, transports

    return create


@pytest.mark.parametrize("code", ["UserNotActiveError", "WrongCredentialsError", "AuthenticationRequiredError"])
def test_inactive_account_is_disabled_once_and_next_account_remains_preferred(code: str, client_factory: ClientFactory) -> None:
    report = vt.Object("file", "hash")
    client, stats, transports = client_factory([[vt.APIError(code, "secret-0")], [report, report]])
    assert client.get_object("/files/{}", "hash") is report
    assert client.get_object("/files/{}", "hash") is report
    client.close()
    first, second = stats.snapshots()
    assert (first.requests, first.failed, first.retries, first.failovers, first.disabled_reason) == (1, 1, 0, 1, code)
    assert (second.requests, second.succeeded) == (2, 2)
    assert len(transports[0].requests) == 1
    assert all(transport.closed for transport in transports)


@pytest.mark.parametrize(
    "failure", [vt.APIError("TransientError", "secret-0"), vt.APIError("ServerError", "private body"), TimeoutError("private body")]
)
def test_temporary_failures_retry_same_account_before_switching(failure: Exception, client_factory: ClientFactory) -> None:
    report = vt.Object("file", "hash")
    client, stats, transports = client_factory([[failure, failure, failure], [report]])
    assert client.get_object("/files/{}", "hash") is report
    first, second = stats.snapshots()
    assert (first.requests, first.failed, first.retries, first.failovers) == (3, 3, 2, 1)
    assert first.disabled_reason == (failure.code if isinstance(failure, vt.APIError) else type(failure).__name__)
    assert second.succeeded == 1
    assert len(transports[0].requests) == 3


@pytest.mark.parametrize("code", ["QuotaExceededError", "TooManyRequestsError"])
def test_quota_retries_are_bounded_and_account_disabled_after_exhaustion(code: str, client_factory: ClientFactory) -> None:
    report = vt.Object("file", "hash")
    client, stats, _transports = client_factory([[vt.APIError(code, "private") for _ in range(3)], [report]])
    assert client.get_object("/files/{}", "hash") is report
    account = stats.snapshots()[0]
    assert (account.requests, account.retries, account.disabled_reason) == (3, 2, code)


@pytest.mark.parametrize(
    ("endpoint", "code", "expected"), [("/files/{}", "NotFoundError", 1), ("/files/{}", "NotAvailableYet", 1), ("/analyses/{}", "NotFoundError", 0)]
)
def test_expected_misses_are_separate_from_failed_analysis_ids(endpoint: str, code: str, expected: int, client_factory: ClientFactory) -> None:
    client, stats, _transports = client_factory([[vt.APIError(code, "private")]])
    with pytest.raises(vt.APIError, match=code):
        client.get_object(endpoint, "id")
    account = stats.snapshots()[0]
    assert (account.requests, account.expected, account.failed, account.retries) == (1, expected, 1 - expected, 0)


@pytest.mark.parametrize("failure", [vt.APIError("BadRequestError", "private"), ValueError("invalid shape"), FileNotFoundError("local file")])
def test_nonretryable_errors_do_not_switch_accounts(failure: Exception, client_factory: ClientFactory) -> None:
    client, stats, transports = client_factory([[failure], [vt.Object("file", "hash")]])
    with pytest.raises(type(failure)):
        client.get_object("/files/{}", "hash")
    assert stats.snapshots()[0].failed == 1
    assert not transports[1].requests


def test_all_inactive_accounts_are_not_requested_again(client_factory: ClientFactory) -> None:
    client, stats, transports = client_factory([[vt.APIError("UserNotActiveError", "private")], [vt.APIError("WrongCredentialsError", "private")]])
    with pytest.raises(vt.APIError, match="WrongCredentialsError"):
        client.get_object("/files/{}", "hash")
    with pytest.raises(AccountsUnavailableError):
        client.get_object("/files/{}", "next-hash")
    assert [account.requests for account in stats.snapshots()] == [1, 1]
    assert all(len(transport.requests) == 1 for transport in transports)


def test_upload_attempts_use_new_urls_and_keep_exact_original_bytes(client_factory: ClientFactory) -> None:
    analysis = vt.Object("analysis", "analysis-id")
    client, stats, transports = client_factory([["https://first", vt.APIError("ServerError", "private"), "https://second", analysis]])
    file = BytesIO(b"prefix-payload")
    file.seek(len(b"prefix-"))
    assert client.scan_file(file, wait_for_completion=False) is analysis
    assert file.tell() == len(b"prefix-")
    assert transports[0].requests == [("upload URL", ""), ("https://first", b"payload"), ("upload URL", ""), ("https://second", b"payload")]
    account = stats.snapshots()[0]
    assert (account.requests, account.succeeded, account.failed, account.retries) == (4, 3, 1, 1)


def test_unknown_api_error_codes_and_messages_never_leak(client_factory: ClientFactory) -> None:
    client, stats, _transports = client_factory([[vt.APIError("secret_credential_value", "private details")]])
    with pytest.raises(vt.APIError) as failure:
        client.get_object("/files/{}", "hash")
    assert failure.value.code == "UnknownAPIError"
    assert "secret_credential_value" not in str(failure.value)
    assert stats.snapshots()[0].errors[0].code == "UnknownAPIError"


def test_deadline_prevents_any_network_request(client_factory: ClientFactory) -> None:
    client, stats, transports = client_factory([[vt.Object("file", "hash")]])
    client.set_request_context("report lookup", time.monotonic() - 1.0)
    with pytest.raises(TimeoutError):
        client.get_object("/files/{}", "hash")
    assert not transports[0].requests
    assert stats.snapshots()[0].requests == 0


def test_pending_analysis_is_expected_without_outage_failure(client_factory: ClientFactory) -> None:
    pending = vt.Object("analysis", "analysis-id", {"status": "in-progress"})
    client, stats, _transports = client_factory([[pending]])
    assert client.get_object("/analyses/{}", "analysis-id") is pending
    account = stats.snapshots()[0]
    assert (account.requests, account.expected, account.failed, account.succeeded) == (1, 1, 0, 0)
    assert account.expected_codes == (("AnalysisPending", 1),)
