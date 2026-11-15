from typing import TypedDict

from rich.console import Console
from rich.filesize import decimal
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import (
    CleanOutcome,
    CommandCleanup,
    Estimate,
    EstimateKind,
    OutcomeStatus,
    Risk,
    TargetScan,
    TargetStatus,
)
from stackops.scripts.python.helpers.helpers_utils.clean_drive_scan import requires_root, total_estimate


class ScanRecord(TypedDict):
    key: str
    title: str
    category: str
    risk: Risk
    status: TargetStatus
    message: str
    selected: bool
    requires_root: bool
    estimate_bytes: int | None
    estimate_kind: EstimateKind
    paths: list[str]
    commands: list[list[str]]


class OutcomeRecord(TypedDict):
    key: str
    status: OutcomeStatus
    freed_bytes: int | None
    message: str


RISK_STYLES: dict[Risk, str] = {"safe": "green", "caution": "yellow", "danger": "bold red"}
OUTCOME_STYLES: dict[OutcomeStatus, str] = {"cleaned": "green", "partial": "yellow", "failed": "red", "skipped": "dim"}


def format_estimate(estimate: Estimate) -> str:
    if estimate.bytes is None:
        return "unknown"
    match estimate.kind:
        case "exact":
            prefix = ""
        case "at_least":
            prefix = "≥ "
        case "at_most":
            prefix = "≤ "
        case "approximate":
            prefix = "~ "
    return prefix + decimal(estimate.bytes)


def describe_action(*, scan: TargetScan, elevated: bool) -> str:
    sudo = " (sudo)" if requires_root(scan.action) and not elevated else ""
    if isinstance(scan.action, CommandCleanup):
        return scan.message + sudo
    return f"""delete {len(scan.paths)} path(s){sudo}"""


def ready_by_size(scans: list[TargetScan]) -> list[TargetScan]:
    return sorted((scan for scan in scans if scan.status == "ready"), key=lambda scan: -(scan.estimate.bytes or 0))


def render_report(*, console: Console, scans: list[TargetScan], auto_keys: set[str], elevated: bool) -> None:
    ready = ready_by_size(scans)
    table = Table(title="🧹 Reclaimable disk space", title_justify="left", show_lines=False)
    table.add_column("", justify="center")
    for column in ("Target", "Category", "Risk"):
        table.add_column(column, no_wrap=True)
    table.add_column("Savings", justify="right", no_wrap=True)
    table.add_column("Action", overflow="fold")
    for scan in ready:
        table.add_row(
            "●" if scan.target.key in auto_keys else "", scan.target.key, scan.target.category.value,
            Text(scan.target.risk, style=RISK_STYLES[scan.target.risk]), format_estimate(scan.estimate), describe_action(scan=scan, elevated=elevated),
        )
    if ready:
        console.print(table)
    selected = [scan for scan in ready if scan.target.key in auto_keys]
    console.print(f"""● selected: {format_estimate(total_estimate(selected))} across {len(selected)} target(s) · everything listed: {format_estimate(total_estimate(ready))}""")
    empty = [scan.target.key for scan in scans if scan.status == "empty"]
    if empty:
        console.print(Text(f"""Nothing to clean: {", ".join(empty)}""", style="dim"))
    missing: dict[str, list[str]] = {}
    for scan in scans:
        if scan.status == "missing_tool":
            missing.setdefault(scan.message, []).append(scan.target.key)
        if scan.status == "failed":
            console.print(Text(f"""Could not measure {scan.target.key}: {scan.message}""", style="yellow"))
    for message, keys in missing.items():
        console.print(Text(f"""Skipped {", ".join(keys)}: {message}""", style="dim"))


def render_outcomes(*, console: Console, outcomes: list[CleanOutcome], free_before: int, free_after: int) -> None:
    table = Table(title="🧹 Cleanup results", title_justify="left")
    table.add_column("Target", overflow="fold")
    table.add_column("Status")
    table.add_column("Freed", justify="right", no_wrap=True)
    table.add_column("Details", overflow="fold")
    for outcome in outcomes:
        table.add_row(
            outcome.key, Text(outcome.status, style=OUTCOME_STYLES[outcome.status]),
            "unknown" if outcome.freed_bytes is None else decimal(outcome.freed_bytes), outcome.message,
        )
    console.print(table)
    change = free_after - free_before
    console.print(f"""Free space on the home filesystem: {decimal(free_before)} → {decimal(free_after)} ({"+" if change >= 0 else "-"}{decimal(abs(change))})""")


def scan_records(*, scans: list[TargetScan], auto_keys: set[str]) -> list[ScanRecord]:
    return [
        {
            "key": scan.target.key, "title": scan.target.title, "category": scan.target.category.value, "risk": scan.target.risk,
            "status": scan.status, "message": scan.message, "selected": scan.target.key in auto_keys and scan.status == "ready",
            "requires_root": requires_root(scan.action), "estimate_bytes": scan.estimate.bytes, "estimate_kind": scan.estimate.kind,
            "paths": [str(measured.path) for measured in scan.paths], "commands": [list(command) for command in scan.commands],
        }
        for scan in scans
    ]


def outcome_records(outcomes: list[CleanOutcome]) -> list[OutcomeRecord]:
    return [{"key": outcome.key, "status": outcome.status, "freed_bytes": outcome.freed_bytes, "message": outcome.message} for outcome in outcomes]
