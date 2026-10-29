"""Backend helpers for launching generated parallel agent layouts."""

from pathlib import Path
from typing import Final, Literal, TypeAlias


AgentParallelBackend: TypeAlias = Literal["tmux", "herdr", "tuios", "aoe"]
AgentParallelBackendOption: TypeAlias = Literal["tmux", "t", "herdr", "h", "tuios", "u", "aoe", "e"]
DEFAULT_AGENT_PARALLEL_BACKEND: Final[AgentParallelBackend] = "tmux"
AGENT_PARALLEL_BACKENDS: Final[tuple[AgentParallelBackend, ...]] = ("tmux", "herdr", "tuios", "aoe")
AGENT_PARALLEL_BACKEND_HELP: Final[str] = "tmux, herdr, tuios, or aoe"


def resolve_agent_parallel_backend(backend: AgentParallelBackendOption | AgentParallelBackend) -> AgentParallelBackend:
    match backend:
        case "tmux" | "t":
            return "tmux"
        case "herdr" | "h":
            return "herdr"
        case "tuios" | "u":
            return "tuios"
        case "aoe" | "e":
            return "aoe"
        case _:
            raise ValueError(f"Unsupported backend '{backend}'. Use {AGENT_PARALLEL_BACKEND_HELP}.")


def run_generated_layout(*, layout_output_path: Path, backend: AgentParallelBackend, agent: str | None = None) -> None:
    match backend:
        case "tmux":
            _run_generated_layout_with_tmux(layout_output_path=layout_output_path)
        case "tuios":
            from stackops.scripts.python.helpers.helpers_agents.agents_parallel_layouts import read_generated_layouts
            from stackops.scripts.python.helpers.helpers_sessions.sessions_impl import run_layouts

            run_layouts(
                sleep_inbetween=0,
                monitor=False,
                parallel_layouts=None,
                kill_upon_completion=False,
                backend="tuios",
                on_conflict="restart",
                exit_mode="backToShell",
                layouts_selected=read_generated_layouts(layout_output_path=layout_output_path),
            )
        case "herdr":
            from stackops.scripts.python.helpers.helpers_agents.agents_parallel_layouts import read_generated_layouts
            from stackops.scripts.python.helpers.helpers_sessions.sessions_herdr import (
                launch_layout_with_herdr,
                show_herdr_launch_summary,
            )

            layouts = read_generated_layouts(layout_output_path=layout_output_path)
            if len(layouts) != 1:
                raise RuntimeError(f"Herdr backend expects one generated layout, found {len(layouts)} in {layout_output_path}")
            show_herdr_launch_summary(summary=launch_layout_with_herdr(layout=layouts[0]))
        case "aoe":
            from stackops.scripts.python.helpers.helpers_agents.agents_parallel_aoe_backend import run_generated_layout_with_aoe

            run_generated_layout_with_aoe(layout_output_path=layout_output_path, agent=agent)
        case _:
            raise ValueError(f"Unsupported backend '{backend}'. Use {AGENT_PARALLEL_BACKEND_HELP}.")


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
