from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from machineconfig.scripts.python import agents


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


def test_ask_defaults_to_direct_prompt() -> None:
    with (
        patch.object(agents, "run_command", return_value=0) as run_command,
        patch.object(agents, "run_command_with_prompt_file", return_value=0) as run_command_with_prompt_file,
    ):
        result = runner.invoke(agents.get_app(), ["ask", "h", "inspect", "the", "repo"])

    assert result.exit_code == 0
    run_command.assert_called_once_with(
        command=[
            "codex",
            "--dangerously-bypass-approvals-and-sandbox",
            "exec",
            "-c",
            'model_reasoning_effort="high"',
            "inspect the repo",
        ]
    )
    run_command_with_prompt_file.assert_not_called()


def test_ask_uses_file_prompt_only_when_requested(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("inspect the repo", encoding="utf-8")

    with (
        patch.object(agents, "run_command", return_value=0) as run_command,
        patch.object(agents, "run_command_with_prompt_file", return_value=0) as run_command_with_prompt_file,
    ):
        result = runner.invoke(agents.get_app(), ["ask", "h", str(prompt_path), "--file-prompt"])

    assert result.exit_code == 0
    run_command.assert_not_called()
    run_command_with_prompt_file.assert_called_once_with(
        command=[
            "codex",
            "--dangerously-bypass-approvals-and-sandbox",
            "exec",
            "-c",
            'model_reasoning_effort="high"',
            "-",
        ],
        prompt_path=prompt_path,
    )
