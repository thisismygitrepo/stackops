from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents import agents_run_impl


def test_build_agent_command_translates_copilot_reasoning_flag() -> None:
    command_line = agents_run_impl.build_agent_command(agent="copilot", prompt_file=Path("/tmp/prompt.md"), reasoning_effort="high")

    assert "--reasoning-effort high" in command_line
    assert "--reasoning high" not in command_line


def test_should_scaffold_prompts_yaml_prefers_repo_for_default_all() -> None:
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="repo", prompts_yaml_path=None, where="all") is True
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="private", prompts_yaml_path=None, where="all") is False


def test_should_scaffold_prompts_yaml_only_creates_requested_non_repo_locations() -> None:
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="private", prompts_yaml_path=None, where="private") is True
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="public", prompts_yaml_path=None, where="public") is True
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="library", prompts_yaml_path=None, where="library") is False
    assert agents_run_impl._should_scaffold_prompts_yaml(location_name="repo", prompts_yaml_path="custom.yaml", where="all") is True
