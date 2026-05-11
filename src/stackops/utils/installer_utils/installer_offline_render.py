from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stackops.utils.installer_utils.installer_offline_models import BinaryExportResult, ExportStepResult, OfflineInstallerOptions, OfflineInstallerReport


def _build_binary_table(*, results: list[BinaryExportResult]) -> Table:
    table = Table(title="Installer binaries", box=box.SIMPLE_HEAVY, expand=True, header_style="bold cyan")
    table.add_column("Binary", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Source", overflow="fold")
    table.add_column("Archive path", overflow="fold")
    for result in results:
        style = {"included": "green", "missing": "yellow", "skipped": "dim"}[result.status]
        table.add_row(result.binary_name, f"[{style}]{result.status}[/{style}]", str(result.source_path), str(result.export_path))
    return table


def _build_steps_table(*, step_results: list[ExportStepResult]) -> Table:
    table = Table(title="Build steps", box=box.SIMPLE_HEAVY, expand=True, header_style="bold cyan")
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Detail", overflow="fold")
    table.add_column("Output", overflow="fold")
    for step in step_results:
        style = {"included": "green", "missing": "yellow", "skipped": "dim"}[step.status]
        table.add_row(step.label, f"[{style}]{step.status}[/{style}]", step.detail, "" if step.output_path is None else str(step.output_path))
    return table


def render_report(*, report: OfflineInstallerReport, options: OfflineInstallerOptions, console: Console) -> None:
    included_count = sum(1 for result in report.binary_results if result.status == "included")
    missing_count = sum(1 for result in report.binary_results if result.status == "missing")
    console.print()
    console.rule("[bold blue]Offline installer summary[/bold blue]")
    console.print(
        Panel(
            "\n".join(
                [
                    f"Platform: {report.platform_name} ({report.arch_name})",
                    f"Output root: {options.output_root}",
                    f"Installer archive: {report.archive_path}",
                    f"Keep unpacked directory: {options.keep_unpacked}",
                    f"Configs enabled: {options.include_configs}",
                    f"UV bundle enabled: {options.include_uv_bundle}",
                ]
            ),
            title="📤 Build configuration",
            border_style="blue",
        )
    )
    console.print(_build_binary_table(results=report.binary_results))
    console.print(_build_steps_table(step_results=report.step_results))
    console.print(
        Panel(
            "\n".join(
                [
                    f"Binaries included: {included_count}",
                    f"Binaries missing: {missing_count}",
                    f"Archive ready: {report.archive_path}",
                ]
            ),
            title="Result",
            border_style="green" if missing_count == 0 else "yellow",
        )
    )
