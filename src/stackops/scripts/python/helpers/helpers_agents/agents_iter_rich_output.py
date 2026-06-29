from pathlib import Path
from time import sleep
from typing import Final

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import clean_agentops_cache
from stackops.scripts.python.helpers.helpers_agents.agents_iter_render import (
    build_agentops_cache_clean_panel,
    build_iter_close_plan_table,
    build_iter_close_summary_table,
    build_iter_status_table,
    build_iter_track_result_panel,
    build_iter_track_start_panel,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_service import (
    close_iter_workspace_plans,
    get_iter_workspace_statuses,
    load_active_iter_workspace_labels,
    plan_iter_workspace_closes,
    resolve_iter_workspace,
    track_iter_workspace_once,
    validate_iter_workspace_track_inputs,
)


_CONSOLE: Final[Console] = Console()


def show_clean_agentops_cache(*, cwd: Path, dry_run: bool) -> None:
    result = clean_agentops_cache(
        cwd=cwd,
        dry_run=dry_run,
        load_active_iter_workspace_labels=load_active_iter_workspace_labels,
        report=_show_progress,
    )
    _CONSOLE.print(build_agentops_cache_clean_panel(result=result))


def show_close_iter_workspaces_loop(
    *,
    workspace_name: str | None,
    all_workspaces: bool,
    continuous: bool,
    retain_previous: int,
    dry_run: bool,
    interval_seconds: int,
) -> None:
    if interval_seconds < 1:
        raise ValueError("Close interval must be greater than zero.")
    while True:
        close_plans = plan_iter_workspace_closes(
            workspace_name=workspace_name,
            all_workspaces=all_workspaces,
            retain_previous=retain_previous,
        )
        _CONSOLE.print(build_iter_close_plan_table(close_plans=close_plans))
        if dry_run:
            _CONSOLE.print(Panel("No tabs were closed.", title="Dry Run", border_style="yellow"))
            return
        results = close_iter_workspace_plans(close_plans=close_plans, report=_show_progress)
        _CONSOLE.print(build_iter_close_summary_table(results=results))
        failed_count = sum(len(result.failed_tabs) for result in results)
        if failed_count > 0 and not continuous:
            raise RuntimeError(f"Failed to close {failed_count} iteration tab(s); see the close result above.")
        if not continuous:
            return
        _CONSOLE.print(Text(f"Next close pass in {interval_seconds} second(s).", style="dim"))
        sleep(interval_seconds)


def show_track_iter_workspace_loop(
    *, workspace_name: str, max_iterations: int, interval_seconds: int, retain_previous: int
) -> None:
    validate_iter_workspace_track_inputs(
        workspace_name=workspace_name,
        max_iterations=max_iterations,
        interval_seconds=interval_seconds,
        retain_previous=retain_previous,
    )
    pinned_workspace = resolve_iter_workspace(workspace_name=workspace_name)
    _CONSOLE.print(
        build_iter_track_start_panel(
            workspace_name=f"{pinned_workspace.label} ({pinned_workspace.workspace_id})",
            max_iterations=max_iterations,
            interval_seconds=interval_seconds,
            retain_previous=retain_previous,
        )
    )
    while True:
        check = track_iter_workspace_once(
            workspace_id=pinned_workspace.workspace_id,
            max_iterations=max_iterations,
            retain_previous=retain_previous,
            report=_show_progress,
        )
        if check.status is not None:
            _CONSOLE.print(build_iter_status_table(statuses=(check.status,)))
        _CONSOLE.print(build_iter_track_result_panel(result=check.track_result))
        if check.close_result is not None:
            _CONSOLE.print(build_iter_close_summary_table(results=(check.close_result,)))
        if check.track_result.phase == "closed":
            return
        _CONSOLE.print(Text(f"Next track check in {interval_seconds} second(s).", style="dim"))
        sleep(interval_seconds)


def show_iter_status(*, retain_previous: int) -> None:
    statuses = get_iter_workspace_statuses(retain_previous=retain_previous)
    if len(statuses) == 0:
        _CONSOLE.print(Panel("No iter workspaces found.", title="Iter Status", border_style="yellow"))
        return
    _CONSOLE.print(build_iter_status_table(statuses=statuses))


def _show_progress(message: str) -> None:
    _CONSOLE.print(Text(message, style="dim"))
