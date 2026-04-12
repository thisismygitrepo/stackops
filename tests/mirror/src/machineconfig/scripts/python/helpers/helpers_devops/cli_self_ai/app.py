from __future__ import annotations

from typer.testing import CliRunner

import machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai.app as cli_self_ai_app


def test_get_app_help_lists_workflow_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(cli_self_ai_app.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "update-installer" in result.stdout
    assert "update-test" in result.stdout
    assert "update-docs" in result.stdout


def test_update_docs_command_dispatches_to_bound_function(monkeypatch) -> None:
    calls: list[str] = []

    def fake_update_docs() -> None:
        calls.append("update-docs")

    monkeypatch.setattr(cli_self_ai_app.update_docs_module, "update_docs", fake_update_docs)
    runner = CliRunner()

    result = runner.invoke(cli_self_ai_app.get_app(), ["update-docs"])

    assert result.exit_code == 0
    assert calls == ["update-docs"]
