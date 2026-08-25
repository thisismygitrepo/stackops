from collections.abc import Sequence
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import (
    DoctorContext,
    DoctorReport,
    DoctorResource,
    DoctorResourceKind,
    DoctorResourceState,
)


_STATE_STYLE: dict[DoctorResourceState, str] = {
    "active": "bold green",
    "available": "cyan",
    "configured": "blue",
    "disabled": "yellow",
    "missing": "dim red",
    "shadowed": "dim yellow",
}
_RESOURCE_TITLES: dict[DoctorResourceKind, str] = {
    "configuration": "Configurations",
    "plugin": "Plugins / extensions",
    "skill": "Skills",
    "instructions": "Instructions considered",
}


def _display_path(*, path: Path, context: DoctorContext) -> str:
    try:
        relative_project_path = path.relative_to(context.project_root)
        return "." if len(relative_project_path.parts) == 0 else f"./{relative_project_path}"
    except ValueError:
        pass
    try:
        relative_home_path = path.relative_to(context.home_directory)
        return "~" if len(relative_home_path.parts) == 0 else f"~/{relative_home_path}"
    except ValueError:
        return str(path)


def _origin_label(*, resource: DoctorResource) -> str:
    match resource.origin:
        case "local":
            return "local"
        case "global":
            return "inherited · global"
        case "admin":
            return "inherited · admin"
        case "system":
            return "bundled · system"


def _present_count(*, report: DoctorReport, kind: DoctorResourceKind) -> int:
    return sum(resource.kind == kind and resource.state != "missing" for resource in report.resources)


def _binary_status(*, report: DoctorReport) -> Text:
    if report.executable.installed is False:
        return Text("missing", style="bold red")
    if report.executable.error is not None:
        return Text("installed · version error", style="yellow")
    return Text("installed", style="bold green")


def _binary_summary(*, report: DoctorReport) -> Text:
    if report.executable.installed is False:
        return Text(f"✗ {report.definition.executable}", style="bold red")
    if report.executable.error is not None:
        return Text(f"! {report.definition.executable}", style="yellow")
    return Text(f"✓ {report.definition.executable}", style="bold green")


def _summary_table(*, reports: Sequence[DoctorReport]) -> Table:
    table = Table(title="Agent health", header_style="bold cyan", show_lines=False)
    table.add_column("Agent", style="bold")
    table.add_column("Binary")
    table.add_column("Version", overflow="fold")
    table.add_column("Cfg", justify="right")
    table.add_column("Plug", justify="right")
    table.add_column("Skill", justify="right")
    table.add_column("Instr", justify="right")
    for report in reports:
        table.add_row(
            Text(report.definition.display_name),
            _binary_summary(report=report),
            Text(report.executable.version or "—"),
            str(_present_count(report=report, kind="configuration")),
            str(_present_count(report=report, kind="plugin")),
            str(_present_count(report=report, kind="skill")),
            str(_present_count(report=report, kind="instructions")),
        )
    return table


def _overview_table(*, report: DoctorReport) -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(overflow="fold")
    executable_path = "—"
    if report.executable.path is not None:
        executable_path = _display_path(path=report.executable.path, context=report.context)
    table.add_row("Agent", Text(f"{report.definition.display_name} ({report.definition.agent})"))
    table.add_row("Binary", _binary_status(report=report))
    table.add_row("Executable", Text(executable_path))
    table.add_row("Version", Text(report.executable.version or "—"))
    if report.executable.error is not None:
        table.add_row("Version error", Text(report.executable.error))
    table.add_row("Inspection", report.definition.support_level)
    table.add_row("Working directory", Text(_display_path(path=report.context.working_directory, context=report.context)))
    table.add_row("Project root", Text(_display_path(path=report.context.project_root, context=report.context)))
    return table


def _resource_table(*, report: DoctorReport, kind: DoctorResourceKind) -> Table:
    table = Table(title=_RESOURCE_TITLES[kind], header_style="bold cyan", show_lines=False)
    table.add_column("Name", style="bold", overflow="fold")
    table.add_column("Source", no_wrap=True)
    table.add_column("State", no_wrap=True)
    table.add_column("Path", overflow="fold")
    table.add_column("Why", overflow="fold")
    resources = tuple(resource for resource in report.resources if resource.kind == kind)
    if len(resources) == 0:
        table.add_row("—", "—", Text("none discovered", style="dim"), "—", "—")
        return table
    for resource in resources:
        table.add_row(
            Text(resource.name),
            Text(_origin_label(resource=resource)),
            Text(resource.state, style=_STATE_STYLE[resource.state]),
            Text(_display_path(path=resource.path, context=report.context)),
            Text(resource.detail),
        )
    return table


def render_doctor_reports(*, console: Console, reports: Sequence[DoctorReport]) -> None:
    console.print(_summary_table(reports=reports))
    if len(reports) != 1:
        console.print("[dim]Run `agents doctor <target>` for the full provenance tables.[/dim]")
        return
    report = reports[0]
    console.print(Panel(_overview_table(report=report), title="Doctor overview", border_style="cyan"))
    resource_kinds: tuple[DoctorResourceKind, ...] = ("configuration", "plugin", "skill", "instructions")
    for kind in resource_kinds:
        console.print(_resource_table(report=report, kind=kind))
    if len(report.definition.notes) > 0:
        notes = Text("\n".join(f"• {note}" for note in report.definition.notes))
        console.print(Panel(notes, title="Notes", border_style="blue"))
