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
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import WorkspaceId
from stackops.scripts.python.helpers.helpers_agents.agents_iter_service import (
    close_iter_workspace_plans,
    get_iter_workspace_statuses,
    load_active_workspace_ids,
    plan_iter_workspace_closes,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_selection import choose_agentops_cache_workspace_id, choose_iter_workspace_id


_CONSOLE: Final[Console] = Console()


def show_clean_agentops_cache(*, cwd: Path, workspace_id: str | None, all_workspaces: bool, interactive: bool, dry_run: bool) -> None:
    selected_workspace_id = WorkspaceId(workspace_id) if workspace_id is not None else None
    if interactive:
        inventory = clean_agentops_cache(
            cwd=cwd, workspace_id=None, dry_run=True, load_active_workspace_ids=load_active_workspace_ids, report=lambda _message: None
        )
        selected_workspace_id = choose_agentops_cache_workspace_id(result=inventory)
    elif not all_workspaces and selected_workspace_id is None:
        raise AssertionError("Validated clean scope did not identify a workspace.")

    result = clean_agentops_cache(
        cwd=cwd, workspace_id=selected_workspace_id, dry_run=dry_run, load_active_workspace_ids=load_active_workspace_ids, report=_show_progress
    )
    _CONSOLE.print(build_agentops_cache_clean_panel(result=result))


def show_close_iter_workspaces_loop(
    *, workspace_id: str | None, all_workspaces: bool, interactive: bool, continuous: bool, retain_previous: int, dry_run: bool, interval_seconds: int
) -> None:
    if interval_seconds < 1:
        raise ValueError("Close interval must be greater than zero.")
    selected_workspace_id = workspace_id
    if interactive:
        statuses = get_iter_workspace_statuses(workspace_id=None, retain_previous=retain_previous)
        selected_workspace_id = choose_iter_workspace_id(statuses=statuses)
    elif not all_workspaces and selected_workspace_id is None:
        raise AssertionError("Validated close scope did not identify a workspace.")

    while True:
        close_plans = plan_iter_workspace_closes(workspace_id=selected_workspace_id, retain_previous=retain_previous)
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


def show_iter_status(*, workspace_id: str | None, all_workspaces: bool, interactive: bool, retain_previous: int) -> None:
    selected_workspace_id = workspace_id
    if interactive:
        picker_statuses = get_iter_workspace_statuses(workspace_id=None, retain_previous=retain_previous)
        selected_workspace_id = choose_iter_workspace_id(statuses=picker_statuses)
    elif not all_workspaces and selected_workspace_id is None:
        raise AssertionError("Validated status scope did not identify a workspace.")

    statuses = get_iter_workspace_statuses(workspace_id=selected_workspace_id, retain_previous=retain_previous)
    if len(statuses) == 0:
        _CONSOLE.print(Panel("No iter workspaces found.", title="Iter Status", border_style="yellow"))
        return
    _CONSOLE.print(build_iter_status_table(statuses=statuses))


def _show_progress(message: str) -> None:
    _CONSOLE.print(Text(message, style="dim"))
