from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_run_impl import build_agent_command


def test_build_agent_command_adds_reasoning_for_copilot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_agents.agents_run_impl.resolve_agent_launch_prefix", lambda agent, repo_root: [])
    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_agents.agents_run_impl.get_repo_root", lambda _path: None)

    command = build_agent_command(agent="copilot", prompt_file=Path("/tmp/prompt.md"), reasoning_effort="high")

    assert "--reasoning high" in command


def test_build_agent_command_ignores_unsupported_reasoning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_agents.agents_run_impl.resolve_agent_launch_prefix", lambda agent, repo_root: [])
    monkeypatch.setattr("stackops.scripts.python.helpers.helpers_agents.agents_run_impl.get_repo_root", lambda _path: None)

    command = build_agent_command(agent="claude", prompt_file=Path("/tmp/prompt.md"), reasoning_effort="high")

    assert "--reasoning" not in command
