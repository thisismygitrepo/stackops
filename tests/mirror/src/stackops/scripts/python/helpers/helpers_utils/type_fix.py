import pytest
from typer.testing import CliRunner

import stackops.scripts.python.helpers.helpers_utils.type_fix as type_fix_module


def test_launch_type_fix_matches_manual_workflow_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_create: dict[str, object] = {}
    captured_run: dict[str, object] = {}

    def fake_agents_create_command(**kwargs: object) -> None:
        captured_create.update(kwargs)

    def fake_terminal_run_command(**kwargs: object) -> None:
        captured_run.update(kwargs)

    monkeypatch.setattr(type_fix_module, "agents_create_command", fake_agents_create_command)
    monkeypatch.setattr(type_fix_module, "terminal_run_command", fake_terminal_run_command)
    runner = CliRunner()

    result = runner.invoke(type_fix_module.get_app(), [])

    assert result.exit_code == 0
    assert captured_create == {
        "agent": "codex",
        "context_path": "./.ai/linters/issues_mypy.md",
        "separator": "### Diagnostic",
        "agent_load": 10,
        "prompt": type_fix_module.PROMPT,
        "job_name": "fix_mypy_issues",
    }
    assert captured_run["layouts_file"] == "./.ai/agents/fix_mypy_issues/layout.json"
    assert captured_run["max_tabs"] == 50
    assert captured_run["on_conflict"] == "restart"


def test_launch_type_fix_passes_overrides_to_wrapped_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_create: dict[str, object] = {}
    captured_run: dict[str, object] = {}

    def fake_agents_create_command(**kwargs: object) -> None:
        captured_create.update(kwargs)

    def fake_terminal_run_command(**kwargs: object) -> None:
        captured_run.update(kwargs)

    monkeypatch.setattr(type_fix_module, "agents_create_command", fake_agents_create_command)
    monkeypatch.setattr(type_fix_module, "terminal_run_command", fake_terminal_run_command)
    runner = CliRunner()

    result = runner.invoke(
        type_fix_module.get_app(),
        ["--agent", "copilot", "--agent-load", "4", "--which-checker", "pyright", "--max-tabs", "80"],
    )

    assert result.exit_code == 0
    assert captured_create["agent"] == "copilot"
    assert captured_create["agent_load"] == 4
    assert captured_create["context_path"] == "./.ai/linters/issues_pyright.md"
    assert captured_create["job_name"] == "fix_pyright_issues"
    assert captured_run["layouts_file"] == "./.ai/agents/fix_pyright_issues/layout.json"
    assert captured_run["max_tabs"] == 80