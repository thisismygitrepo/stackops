"""CLI implementation for sessions run command."""

import typer

from machineconfig.cluster.sessions_managers.session_conflict import SessionConflictAction
from machineconfig.scripts.python.helpers.helpers_sessions.sessions_cli_common import (
    SessionBackendOption,
    choose_tabs_from_layouts,
    load_selected_layouts,
    resolve_layouts_file,
    resolve_standard_backend,
    substitute_home_in_layouts,
)
from machineconfig.scripts.python.helpers.helpers_sessions.sessions_impl import run_layouts


def run_cli(
    ctx: typer.Context,
    layouts_file: str | None,
    choose_layouts: str | None,
    choose_tabs: str | None,
    sleep_inbetween: float,
    parallel_layouts: int | None,
    max_tabs: int,
    max_layouts: int,
    backend: SessionBackendOption,
    on_conflict: SessionConflictAction,
    monitor: bool,
    kill_upon_completion: bool,
    subsitute_home: bool,
) -> None:
    layouts_file_resolved = resolve_layouts_file(ctx, layouts_file)
    try:
        layouts_selected = load_selected_layouts(layouts_file_resolved, choose_layouts)
        layouts_selected = choose_tabs_from_layouts(
            layouts_file_resolved,
            layouts_selected,
            choose_tabs,
        )
        if subsitute_home:
            layouts_selected = substitute_home_in_layouts(layouts_selected)
        backend_resolved = resolve_standard_backend(backend)
        if parallel_layouts is not None and parallel_layouts <= 0:
            raise ValueError("--parallel-layouts must be a positive integer.")
        if parallel_layouts is None and len(layouts_selected) > max_layouts:
            raise ValueError(
                f"Number of layouts {len(layouts_selected)} exceeds the maximum allowed {max_layouts}. Please adjust your layout file."
            )
        if parallel_layouts is not None and parallel_layouts > max_layouts:
            raise ValueError(
                f"--parallel-layouts value {parallel_layouts} exceeds --max-parallel-layouts limit {max_layouts}."
            )
        for a_layout in layouts_selected:
            if len(a_layout["layoutTabs"]) > max_tabs:
                raise ValueError(
                    f"Layout '{a_layout.get('layoutName', 'Unnamed')}' has {len(a_layout['layoutTabs'])} tabs which exceeds the max of {max_tabs}."
                )

        run_layouts(
            sleep_inbetween=sleep_inbetween,
            monitor=monitor,
            parallel_layouts=parallel_layouts,
            kill_upon_completion=kill_upon_completion,
            layouts_selected=layouts_selected,
            backend=backend_resolved,
            on_conflict=on_conflict,
        )
    except ValueError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from e
