from rich import box
from rich.console import Console
from rich.table import Table

from machineconfig.utils.schemas.installer.installer_types import (
    InstallationResult,
    InstallationResultBuckets,
    InstallationResultFailed,
    InstallationResultSameVersion,
    InstallationResultSkipped,
    InstallationResultUpdated,
)


def format_installation_result(result: InstallationResult) -> str:
    match result["kind"]:
        case "skipped":
            return f"""📦️ {result["emoji"]} {result["exeName"]} {result["detail"]}"""
        case "same_version":
            return f"""📦️ {result["emoji"]} {result["exeName"]}, same version: {result["version"]}"""
        case "updated":
            return f"""📦️ {result["emoji"]} {result["exeName"]} updated from {result["oldVersion"]} ➡️ TO ➡️  {result["newVersion"]}"""
        case "failed":
            return f"""📦️ {result["emoji"]} Failed to install `{result["appName"]}` with error: {result["error"]}"""
    raise AssertionError(f"Unexpected installation result kind: {result['kind']}")


def bucket_installation_results(results: list[InstallationResult]) -> InstallationResultBuckets:
    buckets = InstallationResultBuckets(skipped=[], same_version=[], updated=[], failed=[])
    for result in results:
        match result["kind"]:
            case "skipped":
                buckets["skipped"].append(result)
            case "same_version":
                buckets["same_version"].append(result)
            case "updated":
                buckets["updated"].append(result)
            case "failed":
                buckets["failed"].append(result)
    return buckets


def _compact_cell(value: str, empty_value: str) -> str:
    normalized = " ".join(value.split())
    if normalized == "":
        return empty_value
    return normalized


def _build_same_version_table(results: list[InstallationResultSameVersion]) -> Table:
    table = Table(title="✓ Same Version Apps", box=box.SIMPLE_HEAVY, expand=True, header_style="bold cyan")
    table.add_column("App", style="cyan", no_wrap=True)
    table.add_column("Emoji", justify="center", no_wrap=True)
    table.add_column("Version", style="yellow", overflow="fold")
    for result in results:
        table.add_row(
            result["appName"],
            result["emoji"],
            _compact_cell(result["version"], "not detected"),
        )
    return table


def _build_updated_table(results: list[InstallationResultUpdated]) -> Table:
    table = Table(title="⬆️ Updated Apps", box=box.SIMPLE_HEAVY, expand=True, header_style="bold cyan")
    table.add_column("App", style="cyan", no_wrap=True)
    table.add_column("Emoji", justify="center", no_wrap=True)
    table.add_column("Old Version", style="yellow", overflow="fold")
    table.add_column("New Version", style="green", overflow="fold")
    for result in results:
        table.add_row(
            result["appName"],
            result["emoji"],
            _compact_cell(result["oldVersion"], "not detected"),
            _compact_cell(result["newVersion"], "not detected"),
        )
    return table


def _build_skipped_table(results: list[InstallationResultSkipped]) -> Table:
    table = Table(title="⏭️ Skipped Apps", box=box.SIMPLE_HEAVY, expand=True, header_style="bold cyan")
    table.add_column("App", style="cyan", no_wrap=True)
    table.add_column("Emoji", justify="center", no_wrap=True)
    table.add_column("Detail", style="yellow", overflow="fold")
    for result in results:
        table.add_row(
            result["appName"],
            result["emoji"],
            _compact_cell(result["detail"], "n/a"),
        )
    return table


def _build_failed_table(results: list[InstallationResultFailed]) -> Table:
    table = Table(title="❌ Failed Apps", box=box.SIMPLE_HEAVY, expand=True, header_style="bold cyan")
    table.add_column("App", style="cyan", no_wrap=True)
    table.add_column("Emoji", justify="center", no_wrap=True)
    table.add_column("Error", style="red", overflow="fold")
    for result in results:
        table.add_row(
            result["appName"],
            result["emoji"],
            _compact_cell(result["error"], "unknown error"),
        )
    return table


def render_installation_summary(results: list[InstallationResult], console: Console, title: str) -> None:
    console.print()
    console.rule(title)
    if len(results) == 0:
        console.print("[yellow]No installation results.[/yellow]")
        return

    buckets = bucket_installation_results(results=results)
    if len(buckets["same_version"]) > 0:
        console.print(_build_same_version_table(results=buckets["same_version"]))
    if len(buckets["updated"]) > 0:
        console.print(_build_updated_table(results=buckets["updated"]))
    if len(buckets["skipped"]) > 0:
        console.print(_build_skipped_table(results=buckets["skipped"]))
    if len(buckets["failed"]) > 0:
        console.print(_build_failed_table(results=buckets["failed"]))
