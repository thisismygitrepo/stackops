from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python import agents
from machineconfig.scripts.python.helpers.helpers_agents import agents_run_impl
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import reasoning_help, reasoning_support


runner = CliRunner()


def test_build_prompt_command_passes_prompt_directly() -> None:
    command = agents.build_prompt_command(reasoning_effort="high", prompt="inspect the repo")

    assert command == [
        "codex",
        "--dangerously-bypass-approvals-and-sandbox",
        "exec",
        "-c",
        'model_reasoning_effort="high"',
        "inspect the repo",
    ]


def test_build_file_prompt_command_uses_stdin_marker() -> None:
    command = agents.build_file_prompt_command(reasoning_effort="xhigh")

    assert command == [
        "codex",
        "--dangerously-bypass-approvals-and-sandbox",
        "exec",
        "-c",
        'model_reasoning_effort="xhigh"',
        "-",
    ]


def test_build_prompt_command_supports_medium_reasoning() -> None:
    command = agents.build_prompt_command(reasoning_effort="medium", prompt="inspect the repo")

    assert command == [
        "codex",
        "--dangerously-bypass-approvals-and-sandbox",
        "exec",
        "-c",
        'model_reasoning_effort="medium"',
        "inspect the repo",
    ]


def test_ask_defaults_to_direct_prompt() -> None:
    with (
        patch.object(agents, "_write_temporary_prompt_file", return_value=Path("/tmp/ask_prompt.md")) as write_temporary_prompt_file,
        patch.object(agents, "build_ask_command", return_value="codex exec inspect") as build_ask_command,
        patch.object(agents, "run_shell_command", return_value=0) as run_shell_command,
    ):
        result = runner.invoke(agents.get_app(), ["ask", "h", "inspect", "the", "repo"])

    assert result.exit_code == 0
    write_temporary_prompt_file.assert_called_once_with(prompt_text="inspect the repo")
    build_ask_command.assert_called_once_with(agent="codex", prompt_file=Path("/tmp/ask_prompt.md"), reasoning_effort="high")
    run_shell_command.assert_called_once_with(command_line="codex exec inspect")


def test_ask_supports_medium_reasoning_shortcut() -> None:
    with (
        patch.object(agents, "_write_temporary_prompt_file", return_value=Path("/tmp/ask_prompt.md")) as write_temporary_prompt_file,
        patch.object(agents, "build_ask_command", return_value="codex exec inspect") as build_ask_command,
        patch.object(agents, "run_shell_command", return_value=0) as run_shell_command,
    ):
        result = runner.invoke(agents.get_app(), ["ask", "m", "inspect", "the", "repo"])

    assert result.exit_code == 0
    write_temporary_prompt_file.assert_called_once_with(prompt_text="inspect the repo")
    build_ask_command.assert_called_once_with(agent="codex", prompt_file=Path("/tmp/ask_prompt.md"), reasoning_effort="medium")
    run_shell_command.assert_called_once_with(command_line="codex exec inspect")


def test_ask_uses_file_prompt_only_when_requested(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("inspect the repo", encoding="utf-8")

    with (
        patch.object(agents, "_write_temporary_prompt_file") as write_temporary_prompt_file,
        patch.object(agents, "build_ask_command", return_value="codex exec -") as build_ask_command,
        patch.object(agents, "run_shell_command", return_value=0) as run_shell_command,
    ):
        result = runner.invoke(agents.get_app(), ["ask", "h", str(prompt_path), "--file-prompt"])

    assert result.exit_code == 0
    write_temporary_prompt_file.assert_not_called()
    build_ask_command.assert_called_once_with(agent="codex", prompt_file=prompt_path, reasoning_effort="high")
    run_shell_command.assert_called_once_with(command_line="codex exec -")


def test_build_ask_command_supports_copilot_reasoning() -> None:
    command = agents.build_ask_command(agent="copilot", prompt_file=Path("/tmp/prompt.md"), reasoning_effort="high")

    assert command == 'copilot --reasoning-effort high -p "$(cat /tmp/prompt.md)" --yolo'


def test_ask_supports_copilot_via_agent_option() -> None:
    with (
        patch.object(agents, "_write_temporary_prompt_file", return_value=Path("/tmp/copilot_prompt.md")) as write_temporary_prompt_file,
        patch.object(agents, "build_ask_command", return_value="copilot --reasoning-effort high -p ... --yolo") as build_ask_command,
        patch.object(agents, "run_shell_command", return_value=0) as run_shell_command,
    ):
        result = runner.invoke(agents.get_app(), ["ask", "--agent", "copilot", "--reasoning", "h", "inspect", "the", "repo"])

    assert result.exit_code == 0
    write_temporary_prompt_file.assert_called_once_with(prompt_text="inspect the repo")
    build_ask_command.assert_called_once_with(agent="copilot", prompt_file=Path("/tmp/copilot_prompt.md"), reasoning_effort="high")
    run_shell_command.assert_called_once_with(command_line="copilot --reasoning-effort high -p ... --yolo")


def test_ask_help_lists_agent_and_reasoning_options() -> None:
    result = runner.invoke(agents.get_app(), ["a", "--help"])

    assert result.exit_code == 0
    assert "--agent" in result.stdout
    assert "-a" in result.stdout
    assert "--reasoning" in result.stdout
    assert "-r" in result.stdout
    assert "PROMPT..." in result.stdout


def test_parallel_group_exposes_parallel_workflow_commands() -> None:
    result = runner.invoke(agents.get_app(), ["parallel", "--help"])

    assert result.exit_code == 0
    assert "create" in result.stdout
    assert "create-context" in result.stdout
    assert "collect" in result.stdout
    assert "make-template" in result.stdout


def test_parallel_workflow_commands_are_not_top_level_commands() -> None:
    result = runner.invoke(agents.get_app(), ["create", "--help"])

    assert result.exit_code != 0
    assert "No such command 'create'" in result.output


def test_codex_reasoning_help_mentions_medium_and_model_subset_note() -> None:
    assert reasoning_help(agent="codex") == "n=none, l=low, m=medium, h=high, x=xhigh; actual model support can be a narrower subset"


def test_claude_reasoning_support_matches_documented_subset() -> None:
    assert reasoning_support(agent="claude").efforts == ("low", "medium", "high")


def test_run_prompt_help_lists_reasoning_effort_option() -> None:
    result = runner.invoke(agents.get_app(), ["r", "--help"])

    assert result.exit_code == 0
    assert "--reasoning-effort" in result.stdout
    assert "-r" in result.stdout


def test_run_prompt_passes_reasoning_effort_to_impl() -> None:
    with patch("machineconfig.scripts.python.helpers.helpers_agents.agents_run_impl.run") as impl:
        result = runner.invoke(
            agents.get_app(),
            ["r", "--agent", "codex", "--reasoning-effort", "high", "inspect the repo"],
        )

    assert result.exit_code == 0
    impl.assert_called_once_with(
        prompt="inspect the repo",
        agent="codex",
        reasoning_effort="high",
        context=None,
        context_path=None,
        prompts_yaml_path=None,
        context_name=None,
        where="all",
        edit=False,
        show_prompts_yaml_format=False,
    )


def test_build_agent_command_adds_reasoning_effort_for_codex(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("inspect the repo", encoding="utf-8")

    command = agents_run_impl.build_agent_command(agent="codex", prompt_file=prompt_path, reasoning_effort="high")

    assert 'model_reasoning_effort="high"' in command


def test_build_agent_command_rejects_reasoning_effort_for_non_codex(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("inspect the repo", encoding="utf-8")

    with pytest.raises(ValueError, match="--reasoning-effort is only supported for --agent codex"):
        agents_run_impl.build_agent_command(agent="copilot", prompt_file=prompt_path, reasoning_effort="high")
