"""Backend helpers for launching generated parallel agent layouts."""

from pathlib import Path

from stackops.utils.schemas.config.multiplexer_types import SessionMultiplexer


def run_generated_layout(*, layout_output_path: Path, backend: SessionMultiplexer, agent: str | None = None) -> None:
    match backend:
        case "tmux":
            _run_generated_layout_with_tmux(layout_output_path=layout_output_path)
        case "tuios":
            from stackops.scripts.python.helpers.helpers_sessions.sessions_impl import run_layouts
            from stackops.utils.schemas.layouts.layout_file import read_layouts_file

            run_layouts(
                sleep_inbetween=0,
                monitor=False,
                parallel_layouts=None,
                kill_upon_completion=False,
                backend="tuios",
                on_conflict="restart",
                exit_mode="backToShell",
                layouts_selected=read_layouts_file(path=layout_output_path)["layouts"],
            )
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions.sessions_herdr import (
                launch_layout_with_herdr,
                show_herdr_launch_summary,
            )
            from stackops.utils.schemas.layouts.layout_file import read_layouts_file

            layouts = read_layouts_file(path=layout_output_path)["layouts"]
            if len(layouts) != 1:
                raise RuntimeError(f"Herdr backend expects one generated layout, found {len(layouts)} in {layout_output_path}")
            show_herdr_launch_summary(summary=launch_layout_with_herdr(layout=layouts[0]))
        case "aoe":
            from stackops.scripts.python.helpers.helpers_agents.agents_parallel_aoe_backend import run_generated_layout_with_aoe

            run_generated_layout_with_aoe(layout_output_path=layout_output_path, agent=agent)


def _run_generated_layout_with_tmux(*, layout_output_path: Path) -> None:
    from stackops.scripts.python.helpers.helpers_sessions.sessions_cli_run import run_cli

    run_cli(
        ctx=None,
        layouts_file=str(layout_output_path),
        source="all",
        test_layout=False,
        choose_layouts=None,
        choose_tabs=None,
        sleep_inbetween=1.0,
        max_tabs=100,
        max_layouts=25,
        monitor=False,
        parallel_layouts=None,
        backend="tmux",
        on_conflict="restart",
        exit_mode="backToShell",
        kill_upon_completion=False,
        subsitute_home=False,
    )
