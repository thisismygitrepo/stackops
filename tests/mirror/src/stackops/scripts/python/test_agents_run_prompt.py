import shlex
from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents import agents_run_context, agents_run_skill
from stackops.utils import code


@pytest.mark.parametrize("command_name", ["run-prompt", "r"])
@pytest.mark.parametrize("interactive_option", [None, "-i", "--interactive"])
@pytest.mark.parametrize("second_brain", [False, True])
def test_run_prompt_preserves_composed_input_and_directory(
    command_name: str,
    interactive_option: str | None,
    second_brain: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home with spaces"
    second_brain_directory = home.joinpath("code", "agents", "second-brain")
    second_brain_directory.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: home))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(agents_run_skill, "supported_agent_skill_names", lambda: ("review",))
    skill_reference = "Read the review skill at https://example.invalid/skills/review/SKILL.md"
    reference_renderer = Mock(return_value=skill_reference)
    monkeypatch.setattr(agents_run_skill, "render_agent_skill_reference", reference_renderer)
    handoffs: list[tuple[str, bool, Path]] = []

    def capture_shell_handoff(script: str, strict: bool) -> None:
        handoffs.append((script, strict, Path.cwd()))

    monkeypatch.setattr(code, "exit_then_run_shell_script", capture_shell_handoff)
    context = """Context with 'quotes', $HOME, and a newline.
Keep this intact."""
    prompt_parts = ["--interactive", "-i", "explain", "a 'quote'", "$HOME"]
    arguments = [command_name, "--agent", "codex", "--reasoning", "high", "--context", context, "--skill", "review"]
    if interactive_option is not None:
        arguments.append(interactive_option)
    if second_brain:
        arguments.append("--second-brain")
    arguments.extend(["--", *prompt_parts])

    result = CliRunner().invoke(agents.get_app(), arguments)

    assert result.exit_code == 0, result.output
    reference_renderer.assert_called_once_with(skill_name="review")
    prompt_files = tuple(home.joinpath("tmp_results", "tmp_files", "agents").glob("run_prompt_*.md"))
    assert len(prompt_files) == 1
    expected_prompt = f"""# Context
{context}

# Skill
{skill_reference}

# Prompt
{' '.join(prompt_parts)}
"""
    assert prompt_files[0].read_text(encoding="utf-8") == expected_prompt
    assert len(handoffs) == 1
    script, strict, directory = handoffs[0]
    assert strict is False
    expected_directory = second_brain_directory if second_brain else tmp_path
    assert directory == expected_directory
    assert Path.cwd() == tmp_path
    command = shlex.split(script)
    if second_brain:
        assert command[:4] == ["cd", "--", str(second_brain_directory), "&&"]
        command = command[4:]
    assert command[0] == "codex"
    config_values = [command[index + 1] for index, argument in enumerate(command[:-1]) if argument == "-c"]
    assert '''model_reasoning_effort="high"''' in config_values
    if interactive_option is None:
        assert command[1] == "exec"
        assert command[-3:] == ["-", "<", str(prompt_files[0])]
    else:
        assert "exec" not in command
        assert "<" not in command
        assert command[-1] == expected_prompt


@pytest.mark.parametrize("agent", ["oz", "deepseek"])
def test_interactive_unsupported_agent_fails_before_selecting_context(agent: str, monkeypatch: pytest.MonkeyPatch) -> None:
    context_picker = Mock(side_effect=AssertionError("Context selection must not run for an unsupported interactive agent"))
    shell_handoff = Mock(side_effect=AssertionError("An unsupported interactive agent must not launch"))
    monkeypatch.setattr(agents_run_context, "resolve_prompts_yaml_paths", context_picker)
    monkeypatch.setattr(code, "exit_then_run_shell_script", shell_handoff)

    result = CliRunner().invoke(agents.get_app(), ["r", "-i", "--agent", agent, "hello"])

    assert result.exit_code == 2, result.output
    assert agent in result.output.lower()
    context_picker.assert_not_called()
    shell_handoff.assert_not_called()
