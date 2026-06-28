from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive import main as interactive_main
from stackops.scripts.python.helpers.helpers_agents import agents_ask_impl
from stackops.scripts.python.helpers.helpers_agents import agents_iter_impl
from stackops.scripts.python.helpers.helpers_agents import agents_run_impl
from stackops.utils.schemas.fire_agents.fire_agents_types import DEFAULT_AGENT
import stackops.utils.accessories as accessories


def _capture_run_prompt(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str | None, object]]:
    captured_calls: list[tuple[str | None, object]] = []

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
        captured_calls.append((prompt, agent))

    monkeypatch.setattr(agents_run_impl, "run", fake_run)
    return captured_calls


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
    captured_calls = _capture_run_prompt(monkeypatch=monkeypatch)

    result = CliRunner().invoke(agents.get_app(), ["run-prompt", "inspect", "this", "repo"])

    assert result.exit_code == 0, result.output
    assert captured_calls == [("inspect this repo", DEFAULT_AGENT)]


def test_run_prompt_accepts_option_looking_prompt_after_delimiter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls = _capture_run_prompt(monkeypatch=monkeypatch)

    result = CliRunner().invoke(agents.get_app(), ["run-prompt", "--", "review", "--flag-like", "-x"])

    assert result.exit_code == 0, result.output
    assert captured_calls == [("review --flag-like -x", DEFAULT_AGENT)]


def test_parallel_create_context_defaults_to_codex(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured_calls = _capture_run_prompt(monkeypatch=monkeypatch)
    monkeypatch.setattr(accessories, "get_repo_root", lambda path: tmp_path)

    result = CliRunner().invoke(agents.get_app(), ["parallel", "create-context", "split this work", "--job-name", "split-job"])

    assert result.exit_code == 0, result.output
    assert len(captured_calls) == 1
    prompt, agent = captured_calls[0]
    assert agent == DEFAULT_AGENT
    assert prompt is not None
    assert "split this work" in prompt
    assert "./.ai/agents/split-job/context.md" in prompt


def test_ask_defaults_to_shared_default_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_agents: list[object] = []

    def fake_run_ask(prompt_parts: object, agent: object, reasoning: object, file_prompt: object, quiet: bool) -> int:
        captured_agents.append(agent)
        return 0

    monkeypatch.setattr(agents_ask_impl, "run_ask", fake_run_ask)

    result = CliRunner().invoke(agents.get_app(), ["ask", "summarize"])

    assert result.exit_code == 0, result.output
    assert captured_agents == [DEFAULT_AGENT]


def test_interactive_create_defaults_to_codex() -> None:
    assert interactive_main.main.__kwdefaults__ is not None
    assert interactive_main.main.__kwdefaults__["agent"] == DEFAULT_AGENT


def test_add_config_reports_plan_phases_and_files(tmp_path: Path) -> None:
    result = CliRunner().invoke(agents.get_app(), ["add-config", "--agent", "codex", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Agent configuration plan" in result.output
    assert "Configured codex" in result.output
    assert "Configuration complete" in result.output
    assert "Filesystem changes (2)" in result.output
    assert "./.codex/config.toml" in result.output
    assert "./AGENTS.md" in result.output
    config_content = tmp_path.joinpath(".codex", "config.toml").read_text(encoding="utf-8")
    assert "[otel]" not in config_content
    assert "remote_models" not in config_content


def test_add_config_short_alias_is_c(tmp_path: Path) -> None:
    result = CliRunner().invoke(agents.get_app(), ["c", "--agent", "codex", "--root", str(tmp_path), "--no-add-instructions"])

    assert result.exit_code == 0, result.output
    assert tmp_path.joinpath(".codex", "config.toml").is_file()


def test_iter_status_command_calls_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_show_iter_status() -> None:
        calls.append("status")

    monkeypatch.setattr(agents_iter_impl, "show_iter_status", fake_show_iter_status)

    result = CliRunner().invoke(agents.get_app(), ["iter", "status"])

    assert result.exit_code == 0, result.output
    assert calls == ["status"]


def test_iter_clean_command_calls_impl_for_one_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str | None, bool, bool]] = []

    def fake_clean_iter_workspaces_loop(
        *, workspace_name: str | None, all_workspaces: bool, continuous: bool, report: object
    ) -> None:
        calls.append((workspace_name, all_workspaces, continuous))

    monkeypatch.setattr(agents_iter_impl, "clean_iter_workspaces_loop", fake_clean_iter_workspaces_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "clean", "iter-alpha"])

    assert result.exit_code == 0, result.output
    assert calls == [("iter-alpha", False, False)]


def test_iter_clean_all_command_calls_impl_for_all_workspaces(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str | None, bool, bool]] = []

    def fake_clean_iter_workspaces_loop(
        *, workspace_name: str | None, all_workspaces: bool, continuous: bool, report: object
    ) -> None:
        calls.append((workspace_name, all_workspaces, continuous))

    monkeypatch.setattr(agents_iter_impl, "clean_iter_workspaces_loop", fake_clean_iter_workspaces_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "clean", "--all", "--loop"])

    assert result.exit_code == 0, result.output
    assert calls == [(None, True, True)]


def test_iter_track_command_calls_impl_with_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, int]] = []

    def fake_track_iter_workspace_loop(
        *, workspace_name: str, max_iterations: int, interval_seconds: int, report: object
    ) -> None:
        calls.append((workspace_name, max_iterations, interval_seconds))

    monkeypatch.setattr(agents_iter_impl, "track_iter_workspace_loop", fake_track_iter_workspace_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "track", "iter-alpha"])

    assert result.exit_code == 0, result.output
    assert calls == [("iter-alpha", 100, 60)]


def test_iter_track_command_accepts_budget_and_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, int]] = []

    def fake_track_iter_workspace_loop(
        *, workspace_name: str, max_iterations: int, interval_seconds: int, report: object
    ) -> None:
        calls.append((workspace_name, max_iterations, interval_seconds))

    monkeypatch.setattr(agents_iter_impl, "track_iter_workspace_loop", fake_track_iter_workspace_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "track", "iter-alpha", "7", "--interval", "2"])

    assert result.exit_code == 0, result.output
    assert calls == [("iter-alpha", 7, 2)]


def test_iter_short_alias_is_uppercase_i() -> None:
    result = CliRunner().invoke(agents.get_app(), ["I", "--help"])

    assert result.exit_code == 0, result.output
    assert "Iter workflow maintenance" in result.output
    assert "clean" in result.output


def test_add_skill_short_alias_is_s() -> None:
    result = CliRunner().invoke(agents.get_app(), ["s", "--help"])

    assert result.exit_code == 0, result.output
    assert "Add a skill" in result.output


def test_symlink_short_alias_is_uppercase_l() -> None:
    result = CliRunner().invoke(agents.get_app(), ["L", "--help"])

    assert result.exit_code == 0, result.output
    assert "Create symlinks" in result.output
