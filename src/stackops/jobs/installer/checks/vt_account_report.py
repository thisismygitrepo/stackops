import csv
import json
from io import StringIO
from pathlib import Path

from rich.console import Group
from rich.table import Table
from rich.text import Text

from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats


def build_account_report(stats: VirusTotalAccountStats) -> Group:
    accounts = stats.snapshots()
    table = Table(title="VirusTotal Account Request Statistics", show_lines=True)
    table.add_column("Account", overflow="fold")
    for heading in ("Requests", "Success", "Expected", "Failed", "In flight", "Retries", "Failovers"):
        table.add_column(heading, justify="right")
    table.add_column("Disabled reason", overflow="fold")
    errors = Table(title="VirusTotal Request Failure Breakdown")
    for heading in ("Account", "Stage", "Error", "Count"):
        errors.add_column(heading, overflow="fold")
    guidance: dict[str, str] = {}
    for account in accounts:
        table.add_row(
            Text(account.account_name),
            str(account.requests),
            str(account.succeeded),
            str(account.expected),
            str(account.failed),
            str(account.requests - account.succeeded - account.expected - account.failed),
            str(account.retries),
            str(account.failovers),
            Text(account.disabled_reason or "-"),
        )
        for error in account.errors:
            errors.add_row(Text(account.account_name), Text(error.stage), Text(error.code), str(error.count))
        codes = {error.code for error in account.errors}
        if account.disabled_reason is not None:
            codes.add(account.disabled_reason)
        if "UserNotActiveError" in codes:
            guidance["UserNotActiveError"] = "UserNotActiveError: activate the VirusTotal account using its verification email; retrying the same account cannot fix this."
        if codes & {"AuthenticationRequiredError", "WrongCredentialsError"}:
            guidance["authentication"] = "Authentication errors: replace the affected account's invalid API credential."
        if "ForbiddenError" in codes:
            guidance["ForbiddenError"] = "ForbiddenError: check the affected account's permissions and plan."
        if "QuotaExceededError" in codes:
            guidance["QuotaExceededError"] = "QuotaExceededError: the affected account's quota is exhausted; use another account or wait for its quota reset."
        if "TooManyRequestsError" in codes:
            guidance["TooManyRequestsError"] = "TooManyRequestsError: rate limited; requests wait before retrying, then may switch accounts."
    totals = Text(
        f"Total requests: {sum(account.requests for account in accounts)}; "
        f"failed attempts: {sum(account.failed for account in accounts)}; "
        f"retries: {sum(account.retries for account in accounts)}; "
        f"account switches: {sum(account.failovers for account in accounts)}."
    )
    counting = Text("Counts cover actual request attempts, including retries. Expected responses (missing or pending reports) are not failures. In flight counts unfinished attempts if scanning stopped early. Failovers count switches away from an account; retries stay on that account.")
    parts: list[Table | Text] = [table, totals, counting]
    if any(account.errors for account in accounts):
        parts.append(errors)
    parts.extend(Text(line) for line in guidance.values())
    return Group(*parts)


def render_account_csv(stats: VirusTotalAccountStats) -> str:
    buffer = StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(("account_name", "requests", "success", "expected", "failed", "in_flight", "retries", "failovers", "disabled_reason", "errors", "expected_codes"))
    for account in stats.snapshots():
        writer.writerow(
            (
                account.account_name,
                account.requests,
                account.succeeded,
                account.expected,
                account.failed,
                account.requests - account.succeeded - account.expected - account.failed,
                account.retries,
                account.failovers,
                account.disabled_reason or "",
                json.dumps({f"{error.stage}:{error.code}": error.count for error in account.errors}, sort_keys=True),
                json.dumps(dict(account.expected_codes), sort_keys=True),
            )
        )
    return buffer.getvalue()


def write_account_report(stats: VirusTotalAccountStats, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_account_csv(stats), encoding="utf-8")
    return path
