"""Agent of Empires backend for generated parallel agent layouts."""

from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_parallel_layouts import read_generated_layouts
from stackops.scripts.python.helpers.helpers_sessions.sessions_aoe_impl import AoeLaunchOptions, run_layouts_via_aoe


_AOE_AGENT_BY_STACKOPS_AGENT: Final[dict[str, str]] = {
    "claude": "claude",
    "qwen": "qwen",
    "copilot": "copilot",
    "codex": "codex",
    "opencode": "opencode",
    "droid": "droid",
    "pi": "pi",
    "cursor-agent": "cursor",
}


def resolve_aoe_agent_for_stackops_agent(agent: str | None) -> str | None:
    if agent is None:
        return None
    return _AOE_AGENT_BY_STACKOPS_AGENT.get(agent)


def run_generated_layout_with_aoe(*, layout_output_path: Path, agent: str | None = None) -> None:
    layouts = read_generated_layouts(layout_output_path=layout_output_path)
    if len(layouts) == 0:
        raise RuntimeError(f"AoE backend cannot launch {layout_output_path} because it contains no layouts.")

    run_layouts_via_aoe(
        layouts_selected=layouts,
        options=AoeLaunchOptions(
            aoe_bin="aoe",
            agent=resolve_aoe_agent_for_stackops_agent(agent),
            model=None,
            provider=None,
            sandbox=None,
            yolo=False,
            cmd=None,
            extra_agent_args=(),
            env_vars=(),
            force=False,
            dry_run=False,
            sleep_inbetween=1.0,
            tab_command_mode="cmd",
            launch=True,
        ),
    )
