from concurrent.futures import ThreadPoolExecutor
import csv
from io import StringIO
import json
from pathlib import Path

from rich.console import Console

from stackops.jobs.installer.checks.vt_account_report import build_account_report, write_account_report
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats


def test_request_events_are_counted_once_and_snapshots_do_not_change() -> None:
    stats = VirusTotalAccountStats(("inactive@example.invalid", "active@example.invalid"))
    original = stats.snapshots()
    stats.request_started(0)
    stats.failed(0, "report lookup", "UserNotActiveError")
    stats.disabled(0, "UserNotActiveError")
    stats.switched(0, 1)
    stats.request_started(1)
    stats.failed(1, "report lookup", "TransientError")
    stats.retried(1)
    stats.request_started(1)
    stats.expected_response(1, "NotFoundError")
    stats.request_started(1)
    stats.succeeded(1)
    accounts = stats.snapshots()

    assert original[0].requests == 0
    assert accounts[0].requests == accounts[0].failed == accounts[0].failovers == 1
    assert accounts[0].disabled_reason == "UserNotActiveError"
    assert accounts[0].errors[0].stage == "report lookup"
    assert accounts[0].errors[0].count == 1
    assert accounts[1].requests == 3
    assert accounts[1].failed == accounts[1].retries == accounts[1].expected == accounts[1].succeeded == 1
    assert accounts[1].expected_codes == (("NotFoundError", 1),)
    assert accounts[1].failovers == 0
    assert accounts[1].disabled_reason is None


def test_simultaneous_workers_keep_exact_attempt_counts() -> None:
    stats = VirusTotalAccountStats(("account",))

    def complete_request(_request_index: int) -> None:
        stats.request_started(0)
        stats.failed(0, "analysis polling", "TooManyRequestsError")
        stats.retried(0)
        stats.request_started(0)
        stats.succeeded(0)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(complete_request, range(200)))

    account = stats.snapshots()[0]
    assert account.requests == 400
    assert account.failed == account.retries == account.succeeded == 200
    assert account.errors[0].count == 200


def test_report_uses_literal_account_names_and_safe_errors(tmp_path: Path) -> None:
    account_name = "[red]account@example.invalid[/red]"
    secret = "dummy-secret-do-not-show"
    stats = VirusTotalAccountStats((account_name, "healthy"))
    stats.request_started(0)
    stats.failed(0, "report lookup", "UserNotActiveError")
    stats.disabled(0, "UserNotActiveError")
    stats.request_started(0)
    stats.failed(0, "report lookup", secret)
    stats.request_started(1)
    stats.expected_response(1, secret)
    stats.switched(0, 1)
    stats.request_started(1)
    stats.succeeded(1)
    output = StringIO()
    Console(file=output, width=240).print(build_account_report(stats))
    account_path = write_account_report(stats, tmp_path / "accounts.csv")

    displayed = output.getvalue()
    assert account_name in displayed
    assert secret not in displayed
    assert "UserNotActiveError" in displayed
    assert "verification email" in displayed
    assert "InvalidErrorCode" in displayed
    assert "failed attempts: 2" in displayed
    assert "account switches: 1" in displayed
    with account_path.open(newline="") as account_file:
        rows = list(csv.DictReader(account_file))
    assert rows[0]["account_name"] == account_name
    assert rows[0]["requests"] == rows[0]["failed"] == "2"
    assert rows[0]["failovers"] == "1"
    assert json.loads(rows[0]["errors"]) == {"report lookup:InvalidErrorCode": 1, "report lookup:UserNotActiveError": 1}
    assert rows[1]["requests"] == "2"
    assert rows[1]["expected"] == "1"
    assert secret not in account_path.read_text(encoding="utf-8")


def test_unfinished_attempts_are_shown_separately(tmp_path: Path) -> None:
    stats = VirusTotalAccountStats(("interrupted-account",))
    stats.request_started(0)
    output = StringIO()
    Console(file=output, width=240).print(build_account_report(stats))
    account_path = write_account_report(stats, tmp_path / "accounts.csv")
    with account_path.open(newline="") as account_file:
        rows = list(csv.DictReader(account_file))

    assert rows[0]["requests"] == rows[0]["in_flight"] == "1"
    assert rows[0]["failed"] == "0"
    assert "In flight" in output.getvalue()
    assert "unfinished attempts" in output.getvalue()
