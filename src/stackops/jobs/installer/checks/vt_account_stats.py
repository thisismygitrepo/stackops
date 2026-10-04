from collections import Counter
from dataclasses import dataclass, field
from threading import Lock

from stackops.jobs.installer.checks.scan_outcomes import ScanStage


@dataclass(frozen=True, slots=True)
class AccountErrorCount:
    stage: ScanStage
    code: str
    count: int


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    account_name: str
    requests: int
    succeeded: int
    expected: int
    failed: int
    retries: int
    failovers: int
    disabled_reason: str | None
    errors: tuple[AccountErrorCount, ...]
    expected_codes: tuple[tuple[str, int], ...]


@dataclass(slots=True)
class _AccountTotals:
    account_name: str
    requests: int = 0
    succeeded: int = 0
    expected: int = 0
    failed: int = 0
    retries: int = 0
    failovers: int = 0
    disabled_reason: str | None = None
    errors: Counter[tuple[ScanStage, str]] = field(default_factory=Counter)
    expected_codes: Counter[str] = field(default_factory=Counter)


class VirusTotalAccountStats:
    def __init__(self, account_names: tuple[str, ...]) -> None:
        self._accounts = tuple(_AccountTotals(account_name=name) for name in account_names)
        self._lock = Lock()

    def request_started(self, account_index: int) -> None:
        with self._lock:
            self._accounts[account_index].requests += 1

    def succeeded(self, account_index: int) -> None:
        with self._lock:
            self._accounts[account_index].succeeded += 1

    def expected_response(self, account_index: int, error_code: str) -> None:
        safe_code = error_code if error_code.isascii() and error_code.isidentifier() else "InvalidErrorCode"
        with self._lock:
            account = self._accounts[account_index]
            account.expected += 1
            account.expected_codes[safe_code] += 1

    def failed(self, account_index: int, stage: ScanStage, error_code: str) -> None:
        safe_code = error_code if error_code.isascii() and error_code.isidentifier() else "InvalidErrorCode"
        with self._lock:
            account = self._accounts[account_index]
            account.failed += 1
            account.errors[(stage, safe_code)] += 1

    def retried(self, account_index: int) -> None:
        with self._lock:
            self._accounts[account_index].retries += 1

    def switched(self, account_index: int, destination: int) -> None:
        if account_index == destination:
            raise ValueError("VirusTotal failover must switch to another account.")
        with self._lock:
            self._accounts[destination]
            self._accounts[account_index].failovers += 1

    def disabled(self, account_index: int, reason: str) -> None:
        safe_reason = reason if reason.isascii() and reason.isidentifier() else "InvalidErrorCode"
        with self._lock:
            self._accounts[account_index].disabled_reason = safe_reason

    def snapshots(self) -> tuple[AccountSnapshot, ...]:
        with self._lock:
            return tuple(
                AccountSnapshot(
                    account_name=account.account_name,
                    requests=account.requests,
                    succeeded=account.succeeded,
                    expected=account.expected,
                    failed=account.failed,
                    retries=account.retries,
                    failovers=account.failovers,
                    disabled_reason=account.disabled_reason,
                    errors=tuple(
                        AccountErrorCount(stage=stage, code=code, count=count)
                        for (stage, code), count in sorted(account.errors.items())
                    ),
                    expected_codes=tuple(sorted(account.expected_codes.items())),
                )
                for account in self._accounts
            )
