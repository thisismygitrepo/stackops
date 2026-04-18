"""CLI implementation for sessions run-all command."""

import typer

from stackops.cluster.sessions_managers.session_conflict import (
    SessionConflictAction,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_cli_common import (
    DynamicSessionBackendOption,
    substitute_home_in_layouts,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import (
    load_all_layouts_from_source,
    resolve_layout_source,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def run_all_cli(
    ctx: typer.Context,
    layouts_file: str | None,
    test_layout: bool,
    max_parallel_tabs: int,
    poll_seconds: float,
    kill_finished_tabs: bool,
    backend: DynamicSessionBackendOption,
    on_conflict: SessionConflictAction,
    subsitute_home: bool,
) -> None:
    try:
        layout_source = resolve_layout_source(
            ctx=ctx,
            layouts_file=layouts_file,
            test_layout=test_layout,
        )
        layouts_selected = load_all_layouts_from_source(layout_source=layout_source)
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
        from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic import (
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
