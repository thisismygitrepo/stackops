from dataclasses import dataclass
from typing import Literal

import aiohttp
import vt

from stackops.jobs.installer.checks.constants import VT_QUOTA_RETRY_DELAY_SECONDS, VT_RETRY_DELAY_SECONDS

type ErrorAction = Literal["expected", "disable", "retry", "switch", "fail"]

EXPECTED_API_CODES: frozenset[str] = frozenset({"NotFoundError", "NotAvailableYet", "AlreadySubmittedError"})
DISABLED_API_CODES: frozenset[str] = frozenset({"UserNotActiveError", "WrongCredentialsError", "AuthenticationRequiredError"})
QUOTA_API_CODES: frozenset[str] = frozenset({"QuotaExceededError", "TooManyRequestsError"})
TRANSIENT_API_CODES: frozenset[str] = frozenset({"TransientError", "DeadlineExceededError", "ServerError"})
KNOWN_API_CODES: frozenset[str] = (
    EXPECTED_API_CODES
    | DISABLED_API_CODES
    | QUOTA_API_CODES
    | TRANSIENT_API_CODES
    | frozenset(
        {
            "BadRequestError",
            "ForbiddenError",
            "ClientError",
            "UnsupportedOperationError",
            "UnprocessableEntityError",
            "InvalidArgumentError",
            "UnselectiveContentQueryError",
            "UnsupportedContentQueryError",
            "AlreadyExistsError",
            "FailedDependencyError",
        }
    )
)


@dataclass(frozen=True)
class RequestErrorPolicy:
    action: ErrorAction
    code: str
    safe_error: Exception
    retry_delay: float
    disable_after_exhaustion: bool


def classify_request_error(error: Exception) -> RequestErrorPolicy:
    action: ErrorAction = "fail"
    retry_delay = VT_RETRY_DELAY_SECONDS
    disable_after_exhaustion = False
    if isinstance(error, vt.APIError):
        code = error.code if error.code in KNOWN_API_CODES else "UnknownAPIError"
        safe_error: Exception = vt.APIError(code, "VirusTotal request failed.")
        if code in EXPECTED_API_CODES:
            action = "expected"
        elif code in DISABLED_API_CODES:
            action = "disable"
        elif code in QUOTA_API_CODES:
            action = "retry"
            retry_delay = VT_QUOTA_RETRY_DELAY_SECONDS
            disable_after_exhaustion = True
        elif code in TRANSIENT_API_CODES:
            action = "retry"
            disable_after_exhaustion = True
        elif code == "ForbiddenError":
            action = "switch"
    else:
        code = type(error).__name__
        safe_error = error
        if isinstance(error, (TimeoutError, ConnectionError, aiohttp.ClientConnectionError, aiohttp.ClientPayloadError)) and not isinstance(
            error, (aiohttp.ClientSSLError, aiohttp.ClientConnectorCertificateError)
        ):
            action = "retry"
            disable_after_exhaustion = True
    return RequestErrorPolicy(action, code, safe_error, retry_delay, disable_after_exhaustion)
