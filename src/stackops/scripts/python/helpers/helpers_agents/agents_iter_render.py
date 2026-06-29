from collections import Counter
from pathlib import Path

from rich import box
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import AgentopsCacheCleanResult
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    FailedTabClose,
    HerdrAgent,
    HerdrTab,
    IterWorkspaceClose,
    IterWorkspaceClosePlan,
    IterWorkspaceStatus,
    IterWorkspaceTrackResult,
    ProtectedTab,
    SkippedTabClose,
)


def build_agentops_cache_clean_panel(*, result: AgentopsCacheCleanResult) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_row("Repository", escape(str(result.repo_root)))
    table.add_row("Iteration records", escape(_repo_relative_path(path=result.iterations_path, repo_root=result.repo_root)))
    table.add_row("Inactive runs", str(len(result.removed_runs)))
    table.add_row("Protected active", str(len(result.protected_runs)))
    table.add_row("Unmanaged", str(len(result.unmanaged_entries)))
    table.add_row("Paths", str(result.removed_entries))
    if result.dry_run and len(result.removed_runs) > 0:
        table.add_row("Status", "[yellow]dry run; no records removed[/yellow]")
        return Panel(table, title="AgentOps Iteration Records", border_style="yellow")
    if result.removed:
        table.add_row("Status", "[green]inactive records removed[/green]")
        return Panel(table, title="AgentOps Iteration Records", border_style="green")
    table.add_row("Status", "[green]nothing stale to remove[/green]")
    return Panel(table, title="AgentOps Iteration Records", border_style="green")


def build_iter_close_plan_table(*, close_plans: tuple[IterWorkspaceClosePlan, ...]) -> Table:
    table = Table(title=f"Iter Close Plan ({len(close_plans)})", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Workspace", style="bold cyan", overflow="fold", ratio=3)
    table.add_column("Tabs", justify="right", no_wrap=True)
    table.add_column("Close", justify="right", no_wrap=True)
    table.add_column("Retain", justify="right", no_wrap=True)
    table.add_column("Protect", justify="right", no_wrap=True)
    table.add_column("Candidates / protection", overflow="fold", ratio=5)
    if len(close_plans) == 0:
        table.add_row("[yellow]No iter workspaces found.[/yellow]", "-", "-", "-", "-", "-")
        return table
    for plan in close_plans:
        detail = _format_tabs(tabs=plan.closable_tabs)
        protected = _format_protection(protected_tabs=plan.protected_tabs)
        if protected != "-":
            detail = f"{detail}\nprotect: {protected}" if detail != "-" else f"protect: {protected}"
        table.add_row(
            _format_workspace(label=plan.workspace.label, workspace_id=str(plan.workspace.workspace_id)),
            str(len(plan.tabs)),
            str(len(plan.closable_tabs)),
            str(len(plan.retained_tabs)),
            str(len(plan.protected_tabs)),
            detail,
        )
    return table


def build_iter_close_summary_table(*, results: tuple[IterWorkspaceClose, ...]) -> Table:
    total_closed = sum(len(result.closed_tabs) for result in results)
    total_failed = sum(len(result.failed_tabs) for result in results)
    table = Table(title=f"Iter Close Result ({total_closed} closed, {total_failed} failed)", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Workspace", style="bold green", overflow="fold", ratio=3)
    table.add_column("Closed", justify="right", no_wrap=True)
    table.add_column("Absent", justify="right", no_wrap=True)
    table.add_column("Skipped", justify="right", no_wrap=True)
    table.add_column("Failed", justify="right", no_wrap=True)
    table.add_column("Details", overflow="fold", ratio=5)
    if len(results) == 0:
        table.add_row("[yellow]No iter workspaces found.[/yellow]", "-", "-", "-", "-", "-")
        return table
    for result in results:
        detail_parts = [
            _format_tabs(tabs=result.closed_tabs),
            _format_skips(skipped_tabs=result.skipped_tabs),
            _format_failures(failed_tabs=result.failed_tabs),
        ]
        table.add_row(
            _format_workspace(label=result.workspace.label, workspace_id=str(result.workspace.workspace_id)),
            str(len(result.closed_tabs)),
            str(len(result.already_absent_tabs)),
            str(len(result.skipped_tabs)),
            str(len(result.failed_tabs)),
            "\n".join(part for part in detail_parts if part != "-") or "-",
        )
    return table


def build_iter_status_table(*, statuses: tuple[IterWorkspaceStatus, ...]) -> Table:
    table = Table(title=f"Iter Status ({len(statuses)})", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Loop", style="bold", overflow="fold", ratio=3)
    table.add_column("Iter", justify="right", no_wrap=True)
    table.add_column("Agent", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Where", overflow="fold", ratio=2)
    table.add_column("Tabs", no_wrap=True)
    for status in statuses:
        plan = status.plan
        table.add_row(
            status.workspace.label,
            _format_iteration(iteration=status.latest_iteration),
            status.latest_agent.agent if status.latest_agent is not None else "-",
            status.latest_agent.agent_status if status.latest_agent is not None else status.workspace.agent_status,
            _format_agent_where(tab=status.latest_agent_tab, agent=status.latest_agent),
            f"{len(plan.tabs)} total {len(plan.closable_tabs)} close "
            f"{len(plan.retained_tabs)} retain {len(plan.protected_tabs)} protect",
        )
    return table


def build_iter_track_start_panel(
    *, workspace_name: str, max_iterations: int, interval_seconds: int, retain_previous: int
) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    table.add_row("Workspace", escape(workspace_name))
    table.add_row("Budget", f"{max_iterations:03d}")
    table.add_row("Interval", f"{interval_seconds} second(s)")
    table.add_row("Retention", f"latest + {retain_previous} previous")
    return Panel(table, title="Iter Tracker", border_style="blue")


def build_iter_track_result_panel(*, result: IterWorkspaceTrackResult) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    workspace_label = result.workspace.label if result.workspace is not None else str(result.workspace_id)
    table.add_row("Workspace", escape(workspace_label))
    table.add_row("Latest", _format_iteration(iteration=result.latest_iteration))
    table.add_row("Budget", f"{result.max_iterations:03d}")
    table.add_row("Phase", escape(result.phase))
    if result.message is not None:
        table.add_row("Detail", escape(result.message))
    border_style = "red" if result.phase == "failed" else "green"
    return Panel(table, title="Budget Check", border_style=border_style)


def _repo_relative_path(*, path: Path, repo_root: Path) -> str:
    resolved_path = path.resolve(strict=False)
    resolved_root = repo_root.resolve(strict=False)
    try:
        relative_path = resolved_path.relative_to(resolved_root).as_posix()
    except ValueError:
        return str(resolved_path)
    return f"./{relative_path}"


def _format_workspace(*, label: str, workspace_id: str) -> str:
    return f"{escape(label)}\n[dim]{escape(workspace_id)}[/dim]"


def _format_tabs(*, tabs: tuple[HerdrTab, ...]) -> str:
    if len(tabs) == 0:
        return "-"
    return ", ".join(f"#{tab.number} {escape(tab.label)}" for tab in tabs)


def _format_protection(*, protected_tabs: tuple[ProtectedTab, ...]) -> str:
    if len(protected_tabs) == 0:
        return "-"
    reason_counts = Counter(protected.reason for protected in protected_tabs)
    return ", ".join(f"{reason}={count}" for reason, count in sorted(reason_counts.items()))


def _format_skips(*, skipped_tabs: tuple[SkippedTabClose, ...]) -> str:
    if len(skipped_tabs) == 0:
        return "-"
    return "skipped: " + ", ".join(f"{escape(item.tab.label)} ({item.reason})" for item in skipped_tabs)


def _format_failures(*, failed_tabs: tuple[FailedTabClose, ...]) -> str:
    if len(failed_tabs) == 0:
        return "-"
    return "failed: " + ", ".join(f"{escape(item.tab.label)} ({escape(item.message)})" for item in failed_tabs)


def _format_iteration(*, iteration: int | None) -> str:
    return "-" if iteration is None else f"{iteration:03d}"


def _format_agent_where(*, tab: HerdrTab | None, agent: HerdrAgent | None) -> str:
    if tab is not None and agent is not None:
        return f"tab #{tab.number} {tab.tab_id}\n{agent.foreground_cwd}"
    if tab is not None:
        return f"tab #{tab.number} {tab.tab_id}"
    if agent is not None:
        return f"{agent.tab_id}\n{agent.foreground_cwd}"
    return "-"
