from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents import agents_run_impl


def _capture_run_prompt(monkeypatch: pytest.MonkeyPatch) -> list[str | None]:
    captured_prompts: list[str | None] = []

    def fake_run(
        prompt: str | None,
        agent: object,
        reasoning_effort: object,
        context: str | None,
        context_path: str | None,
        prompts_yaml_path: str | None,
        context_name: str | None,
        source: object,
        edit: bool,
        show_prompts_yaml_format: bool,
    ) -> None:
        captured_prompts.append(prompt)

    monkeypatch.setattr(agents_run_impl, "run", fake_run)
    return captured_prompts


def test_apply_headroom_uses_resolved_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return "/opt/bin/headroom"

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    command = agents._apply_headroom(command=["codex", "--dangerously-bypass-approvals-and-sandbox"], agent="codex", headroom=True)

    assert command == ["/opt/bin/headroom", "wrap", "codex", "--", "--dangerously-bypass-approvals-and-sandbox"]


def test_apply_headroom_rejects_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return None

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    with pytest.raises(ValueError, match="Required command not found: headroom"):
        agents._apply_headroom(command=["codex"], agent="codex", headroom=True)


def test_apply_headroom_rejects_unsupported_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return "/opt/bin/headroom"

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    with pytest.raises(ValueError, match="headroom does not support opencode"):
        agents._apply_headroom(command=["omp"], agent="opencode", headroom=True)


def test_run_prompt_accepts_unquoted_prompt_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_prompts = _capture_run_prompt(monkeypatch=monkeypatch)

    result = CliRunner().invoke(agents.get_app(), ["run-prompt", "inspect", "this", "repo"])

    assert result.exit_code == 0, result.output
    assert captured_prompts == ["inspect this repo"]


def test_run_prompt_accepts_option_looking_prompt_after_delimiter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_prompts = _capture_run_prompt(monkeypatch=monkeypatch)

    result = CliRunner().invoke(agents.get_app(), ["run-prompt", "--", "review", "--flag-like", "-x"])

    assert result.exit_code == 0, result.output
    assert captured_prompts == ["review --flag-like -x"]


def test_add_config_reports_plan_phases_and_files(tmp_path: Path) -> None:
    result = CliRunner().invoke(agents.get_app(), ["add-config", "--agent", "codex", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Agent configuration plan" in result.output
    assert "Configured codex" in result.output
    assert "Configuration complete" in result.output
    assert "Filesystem changes (2)" in result.output
    assert "./.codex/config.toml" in result.output
    assert "./AGENTS.md" in result.output
