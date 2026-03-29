"""CLI implementation for sessions run-all command."""

import typer

from machineconfig.cluster.sessions_managers.session_conflict import (
    SessionConflictAction,
)
from machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_common import (
    DynamicSessionBackendOption,
    load_all_layouts,
    resolve_layouts_file,
    substitute_home_in_layouts,
)
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def run_all_cli(
    ctx: typer.Context,
    layouts_file: str | None,
    max_parallel_tabs: int,
    poll_seconds: float,
    kill_finished_tabs: bool,
    backend: DynamicSessionBackendOption,
    on_conflict: SessionConflictAction,
    subsitute_home: bool,
) -> None:
    layouts_file_resolved = resolve_layouts_file(ctx, layouts_file)
    try:
        layouts_selected = load_all_layouts(layouts_file_resolved)
        if subsitute_home:
            layouts_selected = substitute_home_in_layouts(layouts_selected)
        merged_tabs = [
            tab
            for layout in layouts_selected
            for tab in layout["layoutTabs"]
        ]
        if len(merged_tabs) == 0:
            raise ValueError("No tabs found across all layouts in the selected file.")
        dynamic_layout: LayoutConfig = {
            "layoutName": "all-layouts-dynamic",
            "layoutTabs": merged_tabs,
        }
        from machineconfig.scripts.python.helpers.helpers_sessions.sessions_dynamic import (
            run_dynamic as run_dynamic_impl,
        )

        run_dynamic_impl(
            layout=dynamic_layout,
            max_parallel_tabs=max_parallel_tabs,
            kill_finished_tabs=kill_finished_tabs,
            backend=backend,
            on_conflict=on_conflict,
            poll_seconds=poll_seconds,
        )
    except ValueError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from e
