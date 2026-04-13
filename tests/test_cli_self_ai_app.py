from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai.app import get_app
from machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai.update_docs import should_include_docs_context_path


def test_workflow_help_lists_update_docs_command() -> None:
    runner = CliRunner()
    result = runner.invoke(get_app(), ["--help"])

    assert result.exit_code == 0
    assert "fix-types" in result.stdout
    assert "update-docs" in result.stdout
    assert "Create an agents layout for updating CLI and API" in result.stdout
    assert "docs only." in result.stdout


def test_update_docs_context_is_limited_to_cli_and_api_docs() -> None:
    assert should_include_docs_context_path(relative_path=Path("docs/cli/devops.md"))
    assert should_include_docs_context_path(relative_path=Path("docs/api/index.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/index.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/guide/overview.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/assets/before.png"))
