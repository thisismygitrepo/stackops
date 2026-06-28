from pathlib import Path
from time import sleep
from typing import Final

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_iter_impl import (
    LOOP_INTERVAL_SECONDS,
    HerdrTab,
    IterWorkspaceClose,
    IterWorkspaceClosePlan,
    IterWorkspaceTrackResult,
    build_iter_status_table,
    close_iter_workspace_plans,
    get_iter_workspace_statuses,
    plan_iter_workspace_closes,
    track_iter_workspace_once,
    validate_iter_workspace_track_inputs,
)
from stackops.scripts.python.helpers.helpers_agents.agents_workflow_cache import (
    WorkflowCacheCleanResult,
    clean_workflow_cache,
)

_CONSOLE: Final[Console] = Console()


def show_clean_workflow_cache(*, cwd: Path) -> None:
    result = clean_workflow_cache(cwd=cwd, report=_ignore_report)
    _CONSOLE.print(build_workflow_cache_clean_panel(result=result))


def show_close_iter_workspaces_loop(*, workspace_name: str | None, all_workspaces: bool, continuous: bool) -> None:
    while True:
        close_plans = plan_iter_workspace_closes(workspace_name=workspace_name, all_workspaces=all_workspaces)
        _CONSOLE.print(build_iter_close_plan_table(close_plans=close_plans))
        summaries = close_iter_workspace_plans(close_plans=close_plans, report=_show_close_progress)
        _CONSOLE.print(build_iter_close_summary_table(summaries=summaries))
        if not continuous:
            return
        _CONSOLE.print(Text(f"Next close pass in {LOOP_INTERVAL_SECONDS} second(s).", style="dim"))
        sleep(LOOP_INTERVAL_SECONDS)


def show_track_iter_workspace_loop(*, workspace_name: str, max_iterations: int, interval_seconds: int, close_old_tabs: bool) -> None:
    validate_iter_workspace_track_inputs(
        workspace_name=workspace_name,
        max_iterations=max_iterations,
        interval_seconds=interval_seconds,
    )
    _CONSOLE.print(
        build_iter_track_start_panel(
            workspace_name=workspace_name,
            max_iterations=max_iterations,
            interval_seconds=interval_seconds,
            close_old_tabs=close_old_tabs,
        )
    )
    while True:
        check = track_iter_workspace_once(
            workspace_name=workspace_name,
            max_iterations=max_iterations,
            close_old_tabs=close_old_tabs,
            report=_ignore_report,
        )
        _CONSOLE.print(build_iter_status_table(statuses=(check.status,)))
        _CONSOLE.print(build_iter_track_result_panel(result=check.budget))
        if check.close_summary is not None:
            _CONSOLE.print(build_iter_close_summary_table(summaries=(check.close_summary,)))
        if check.budget.closed:
            return
        _CONSOLE.print(Text(f"Next track check in {interval_seconds} second(s).", style="dim"))
        sleep(interval_seconds)


def show_iter_status() -> None:
    statuses = get_iter_workspace_statuses()
    if len(statuses) == 0:
        _CONSOLE.print(Panel("No iter workspaces found.", title="Iter Status", border_style="yellow"))
        return
    _CONSOLE.print(build_iter_status_table(statuses=statuses))


def build_workflow_cache_clean_panel(*, result: WorkflowCacheCleanResult) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_row("Repository", escape(str(result.repo_root)))
    table.add_row("Cache", escape(_repo_relative_path(path=result.cache_path, repo_root=result.repo_root)))
    table.add_row("Entries", str(result.removed_entries))
    if result.removed:
        table.add_row("Status", "[green]removed[/green]")
        return Panel(table, title="Workflow Cache", border_style="green")
    table.add_row("Status", "[yellow]not found[/yellow]")
    return Panel(table, title="Workflow Cache", border_style="yellow")


def build_iter_close_plan_table(*, close_plans: tuple[IterWorkspaceClosePlan, ...]) -> Table:
    table = Table(title=f"Iter Close Plan ({len(close_plans)})", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Workspace", style="bold cyan", overflow="fold", ratio=3)
    table.add_column("Tabs", justify="right", no_wrap=True)
    table.add_column("Close", justify="right", no_wrap=True)
    table.add_column("Keep", justify="right", no_wrap=True)
    table.add_column("Guard", justify="right", no_wrap=True)
    table.add_column("Closable Tabs", overflow="fold", ratio=4)
    if len(close_plans) == 0:
        table.add_row("[yellow]No iter workspaces found.[/yellow]", "-", "-", "-", "-", "-")
        return table
    for close_plan in close_plans:
        table.add_row(
            _format_workspace_label(label=close_plan.workspace.label, workspace_id=close_plan.workspace.workspace_id),
            str(len(close_plan.tabs)),
            str(len(close_plan.closable_tabs)),
            str(len(close_plan.kept_tabs)),
            str(len(close_plan.guarded_tabs)),
            _format_close_tabs(tabs=close_plan.closable_tabs),
        )
    return table


def build_iter_close_summary_table(*, summaries: tuple[IterWorkspaceClose, ...]) -> Table:
    total_closed = sum(len(summary.closed_tabs) for summary in summaries)
    table = Table(title=f"Iter Close Result ({total_closed} closed)", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Workspace", style="bold green", overflow="fold", ratio=3)
    table.add_column("Closed", justify="right", no_wrap=True)
    table.add_column("Kept", justify="right", no_wrap=True)
    table.add_column("Guard", justify="right", no_wrap=True)
    table.add_column("Closed Tabs", overflow="fold", ratio=4)
    if len(summaries) == 0:
        table.add_row("[yellow]No iter workspaces found.[/yellow]", "-", "-", "-", "-")
        return table
    for summary in summaries:
        table.add_row(
            _format_workspace_label(label=summary.workspace.label, workspace_id=summary.workspace.workspace_id),
            str(len(summary.closed_tabs)),
            str(len(summary.kept_tabs)),
            str(len(summary.guarded_tabs)),
            _format_close_tabs(tabs=summary.closed_tabs),
        )
    return table


def build_iter_track_start_panel(*, workspace_name: str, max_iterations: int, interval_seconds: int, close_old_tabs: bool) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_row("Workspace", escape(workspace_name))
    table.add_row("Budget", f"{max_iterations:03d}")
    table.add_row("Interval", f"{interval_seconds} second(s)")
    table.add_row("Close old tabs", "yes" if close_old_tabs else "no")
    return Panel(table, title="Iter Tracker", border_style="blue")


def build_iter_track_result_panel(*, result: IterWorkspaceTrackResult) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_row("Workspace", _format_workspace_label(label=result.workspace.label, workspace_id=result.workspace.workspace_id))
    table.add_row("Latest", _format_iteration(iteration=result.latest_iteration))
    table.add_row("Budget", f"{result.max_iterations:03d}")
    if result.closed:
        table.add_row("Decision", "[red]closed workspace[/red]")
        return Panel(table, title="Budget Check", border_style="red")
    if result.latest_iteration is None:
        table.add_row("Decision", "[yellow]no numbered iter agents found[/yellow]")
        return Panel(table, title="Budget Check", border_style="yellow")
    table.add_row("Decision", "[green]keeping workspace open[/green]")
    return Panel(table, title="Budget Check", border_style="green")


def _repo_relative_path(*, path: Path, repo_root: Path) -> str:
    path_resolved = path.expanduser().resolve(strict=False)
    repo_root_resolved = repo_root.expanduser().resolve(strict=False)
    try:
        relative_path = path_resolved.relative_to(repo_root_resolved).as_posix()
    except ValueError:
        return str(path_resolved)
    if relative_path == ".":
        return str(repo_root_resolved)
    return f"./{relative_path}"


def _format_workspace_label(*, label: str, workspace_id: str) -> str:
    return f"{escape(label)}\n[dim]{escape(workspace_id)}[/dim]"


def _format_close_tabs(*, tabs: tuple[HerdrTab, ...]) -> str:
    if len(tabs) == 0:
        return "[dim]-[/dim]"
    return "\n".join(
        f"#{tab.number} {escape(tab.label)} [dim]{escape(tab.agent_status)} {escape(tab.tab_id)}[/dim]"
        for tab in tabs
    )


def _format_iteration(*, iteration: int | None) -> str:
    if iteration is None:
        return "[dim]-[/dim]"
    return f"{iteration:03d}"


def _show_close_progress(message: str) -> None:
    _CONSOLE.print(Text(message, style="dim"))


def _ignore_report(_message: str) -> None:
    return
