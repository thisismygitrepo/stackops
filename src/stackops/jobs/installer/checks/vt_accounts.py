import time
from dataclasses import dataclass
from threading import Event, Lock

from stackops.jobs.installer.checks.constants import VT_LOCK_POLL_INTERVAL_SECONDS
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.secrets.readers import VirusTotalApiKey


class AccountsUnavailableError(ValueError):
    pass


@dataclass
class AccountState:
    credential: VirusTotalApiKey
    request_lock: Lock
    available: bool
    next_request_at: float


class VtAccountPool:
    def __init__(self, credentials: tuple[VirusTotalApiKey, ...], stats: VirusTotalAccountStats) -> None:
        if not credentials:
            raise ValueError("At least one VirusTotal account is required.")
        self.accounts = tuple(AccountState(credential, Lock(), True, 0.0) for credential in credentials)
        self.stats = stats


def wait_for_request(seconds: float, stop: Event, deadline: float) -> None:
    remaining = deadline - time.monotonic()
    if stop.is_set():
        raise InterruptedError("VirusTotal scanning was cancelled.")
    if remaining <= 0:
        raise TimeoutError("VirusTotal analysis deadline was reached.")
    if stop.wait(min(max(0.0, seconds), remaining)):
        raise InterruptedError("VirusTotal scanning was cancelled.")
    if time.monotonic() >= deadline:
        raise TimeoutError("VirusTotal analysis deadline was reached.")


def acquire_request_lock(account: AccountState, stop: Event, deadline: float) -> None:
    while True:
        if stop.is_set():
            raise InterruptedError("VirusTotal scanning was cancelled.")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("VirusTotal analysis deadline was reached.")
        if account.request_lock.acquire(timeout=min(VT_LOCK_POLL_INTERVAL_SECONDS, remaining)):
            return
