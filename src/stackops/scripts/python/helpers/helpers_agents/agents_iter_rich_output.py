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
from stackops.scripts.python.helpers.helpers_agents.agents_iter_service import (
    close_iter_workspace_plan,
    get_iter_workspace_statuses,
    load_active_workspace_ids,
    plan_iter_workspace_close,
)


_CONSOLE: Final[Console] = Console()


def show_clean_agentops_cache(*, cwd: Path, dry_run: bool) -> None:
    result = clean_agentops_cache(cwd=cwd, dry_run=dry_run, load_active_workspace_ids=load_active_workspace_ids, report=_show_progress)
    _CONSOLE.print(build_agentops_cache_clean_panel(result=result))


def show_close_iter_workspace_loop(
    *, cwd: Path, workspace_id: str, continuous: bool, retain_previous: int, dry_run: bool, interval_seconds: int
) -> None:
    if interval_seconds < 1:
        raise ValueError("Close interval must be greater than zero.")
    while True:
        close_plan = plan_iter_workspace_close(cwd=cwd, workspace_id=workspace_id, retain_previous=retain_previous)
        _CONSOLE.print(build_iter_close_plan_table(close_plans=(close_plan,)))
        if dry_run:
            _CONSOLE.print(Panel("No tabs were closed.", title="Dry Run", border_style="yellow"))
            return
        result = close_iter_workspace_plan(cwd=cwd, close_plan=close_plan, report=_show_progress)
        _CONSOLE.print(build_iter_close_summary_table(results=(result,)))
        if len(result.failed_tabs) > 0 and not continuous:
            raise RuntimeError(f"Failed to close {len(result.failed_tabs)} iteration tab(s); see the close result above.")
        if not continuous:
            return
        _CONSOLE.print(Text(f"Next close pass in {interval_seconds} second(s).", style="dim"))
        sleep(interval_seconds)


def show_iter_status(*, cwd: Path, retain_previous: int) -> None:
    statuses = get_iter_workspace_statuses(cwd=cwd, retain_previous=retain_previous)
    if len(statuses) == 0:
        _CONSOLE.print(Panel("No iter workspaces found.", title="Iter Status", border_style="yellow"))
        return
    _CONSOLE.print(build_iter_status_table(statuses=statuses))


def _show_progress(message: str) -> None:
    _CONSOLE.print(Text(message, style="dim"))
