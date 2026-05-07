from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents import agents_run_impl


def test_build_agent_command_translates_copilot_reasoning_flag() -> None:
    command_line = agents_run_impl.build_agent_command(agent="copilot", prompt_file=Path("/tmp/prompt.md"), reasoning_effort="high")

    assert "--reasoning-effort high" in command_line
    assert "--reasoning high" not in command_line
