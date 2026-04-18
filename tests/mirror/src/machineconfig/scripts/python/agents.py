import importlib
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

agents_module = importlib.import_module("machineconfig.scripts.python.agents")


def test_join_prompt_parts_normalizes_prompt_text() -> None:
    assert agents_module._join_prompt_parts(prompt_parts=["  hello", "world  "]) == "hello world"


def test_join_prompt_parts_rejects_empty_prompt() -> None:
    with pytest.raises(typer.BadParameter, match="prompt must not be empty"):
        agents_module._join_prompt_parts(prompt_parts=[" ", ""])


def test_resolve_prompt_path_expands_home_and_requires_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("question", encoding="utf-8")

    resolved_path = agents_module._resolve_prompt_path(prompt_path=Path("~/prompt.md"))

    assert resolved_path == prompt_path.resolve()

    with pytest.raises(typer.BadParameter, match="prompt file does not exist"):
        agents_module._resolve_prompt_path(prompt_path=Path("~/missing.md"))


def test_compose_ask_prompt_text_appends_file_contents(tmp_path: Path) -> None:
    prompt_path = tmp_path / "README.md"
    prompt_path.write_text("# Title\nbody", encoding="utf-8")

    composed_prompt = agents_module._compose_ask_prompt_text(prompt_parts=["summarize", "this"], file_prompt=prompt_path)

    assert composed_prompt == f"""summarize this

--- BEGIN FILE {prompt_path.resolve()} ---
# Title
body
--- END FILE {prompt_path.resolve()} ---"""


def test_build_ask_command_rejects_reasoning_for_unsupported_agent() -> None:
    with pytest.raises(ValueError, match="--reasoning is only supported"):
        agents_module.build_ask_command(agent="claude", prompt_file=Path("/tmp/prompt.md"), reasoning_effort="low")


def test_split_legacy_ask_reasoning_only_consumes_shortcuts_for_supported_agents() -> None:
    shortcut, prompt_parts = agents_module._split_legacy_ask_reasoning(agent="codex", reasoning=None, prompt_parts=["m", "explain", "this"])

    assert shortcut == "m"
    assert prompt_parts == ["explain", "this"]

    unsupported_shortcut, unsupported_prompt_parts = agents_module._split_legacy_ask_reasoning(
        agent="claude", reasoning=None, prompt_parts=["m", "keep", "all"]
    )

    assert unsupported_shortcut is None
    assert unsupported_prompt_parts == ["m", "keep", "all"]


def test_ask_removes_temporary_prompt_file_after_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    created_paths: list[Path] = []
    captured: dict[str, str] = {}

    def fake_write_temporary_prompt_file(prompt_text: str) -> Path:
        prompt_path = tmp_path / "prompt.md"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        created_paths.append(prompt_path)
        return prompt_path

    def fake_build_ask_command(agent: str, prompt_file: Path, reasoning_effort: str | None) -> str:
        captured["agent"] = agent
        captured["prompt_text"] = prompt_file.read_text(encoding="utf-8")
        captured["reasoning_effort"] = "" if reasoning_effort is None else reasoning_effort
        return f"ask {prompt_file.name}"

    def fake_run_shell_command(command_line: str) -> int:
        captured["command_line"] = command_line
        return 7

    monkeypatch.setattr(agents_module, "_write_temporary_prompt_file", fake_write_temporary_prompt_file)
    monkeypatch.setattr(agents_module, "build_ask_command", fake_build_ask_command)
    monkeypatch.setattr(agents_module, "run_shell_command", fake_run_shell_command)

    with pytest.raises(typer.Exit) as exit_info:
        agents_module.ask(prompt=["hello", "world"], agent="codex", reasoning=None, file_prompt=None)

    assert exit_info.value.exit_code == 7
    assert captured == {"agent": "codex", "prompt_text": "hello world", "reasoning_effort": "", "command_line": "ask prompt.md"}
    assert created_paths[0].exists() is False


def test_ask_cli_accepts_prompt_text_with_file_prompt_option(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prompt_path = tmp_path / "README.md"
    prompt_path.write_text("body", encoding="utf-8")
    created_paths: list[Path] = []
    captured: dict[str, str] = {}

    def fake_write_temporary_prompt_file(prompt_text: str) -> Path:
        temporary_prompt_path = tmp_path / "prompt.md"
        temporary_prompt_path.write_text(prompt_text, encoding="utf-8")
        created_paths.append(temporary_prompt_path)
        captured["prompt_text"] = prompt_text
        return temporary_prompt_path

    def fake_build_ask_command(agent: str, prompt_file: Path, reasoning_effort: str | None) -> str:
        captured["agent"] = agent
        captured["reasoning_effort"] = "" if reasoning_effort is None else reasoning_effort
        captured["prompt_file_name"] = prompt_file.name
        return "ask prompt.md"

    def fake_run_shell_command(command_line: str) -> int:
        captured["command_line"] = command_line
        return 0

    monkeypatch.setattr(agents_module, "_write_temporary_prompt_file", fake_write_temporary_prompt_file)
    monkeypatch.setattr(agents_module, "build_ask_command", fake_build_ask_command)
    monkeypatch.setattr(agents_module, "run_shell_command", fake_run_shell_command)

    result = CliRunner().invoke(agents_module.get_app(), ["ask", "summarize this", "-f", str(prompt_path)])

    assert result.exit_code == 0
    assert result.exception is None
    assert captured == {
        "prompt_text": f"""summarize this

--- BEGIN FILE {prompt_path.resolve()} ---
body
--- END FILE {prompt_path.resolve()} ---""",
        "agent": "codex",
        "reasoning_effort": "",
        "prompt_file_name": "prompt.md",
        "command_line": "ask prompt.md",
    }
    assert created_paths[0].exists() is False
