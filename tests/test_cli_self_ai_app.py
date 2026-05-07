

from pathlib import Path
from typing import Literal

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops.cli_self_ai.app import get_app
from stackops.scripts.python.helpers.helpers_devops.cli_self_ai import update_docs, update_installer, update_logic, update_test
from stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_docs import should_include_docs_context_path


def test_workflow_help_lists_update_docs_command() -> None:
    runner = CliRunner()
    result = runner.invoke(get_app(), ["--help"])

    assert result.exit_code == 0
    assert "update-docs" in result.stdout
    assert "Create an agents layout for updating CLI and API" in result.stdout
    assert "docs only." in result.stdout
    assert "update-logic" in result.stdout


def test_update_docs_context_is_limited_to_cli_and_api_docs() -> None:
    assert should_include_docs_context_path(relative_path=Path("docs/cli/devops.md"))
    assert should_include_docs_context_path(relative_path=Path("docs/api/index.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/index.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/guide/overview.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/assets/before.png"))


def _prepare_fake_repo_root(*, tmp_path: Path) -> None:
    tmp_path.joinpath("pyproject.toml").write_text("[project]\nname = \"stackops\"\n", encoding="utf-8")


def _patch_docs_workflow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_developer_repo_root() -> Path:
        return tmp_path

    def fake_build_docs_context(*, repo_root: Path) -> str:
        assert repo_root == tmp_path
        return "docs/cli/devops.md"

    monkeypatch.setattr(update_docs, "get_developer_repo_root", fake_get_developer_repo_root)
    monkeypatch.setattr(update_docs, "_build_docs_context", fake_build_docs_context)


def _patch_test_workflow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_developer_repo_root() -> Path:
        return tmp_path

    def fake_build_repo_python_context(*, repo_root: Path) -> str:
        assert repo_root == tmp_path
        return "src/stackops/example.py"

    monkeypatch.setattr(update_test, "get_developer_repo_root", fake_get_developer_repo_root)
    monkeypatch.setattr(update_test, "_build_repo_python_context", fake_build_repo_python_context)


def _patch_logic_workflow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_developer_repo_root() -> Path:
        return tmp_path

    def fake_build_cli_graph() -> dict[str, object]:
        return {
            "root": {
                "children": [
                    {
                        "kind": "command",
                        "fullPath": "devops w update-logic",
                        "source": {"file": "src/stackops/scripts/python/devops.py"},
                    }
                ]
            }
        }

    monkeypatch.setattr(update_logic, "get_developer_repo_root", fake_get_developer_repo_root)
    monkeypatch.setattr(update_logic, "build_cli_graph", fake_build_cli_graph)


def _patch_installer_workflow(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_developer_repo_root() -> Path:
        return tmp_path

    monkeypatch.setattr(update_installer, "get_developer_repo_root", fake_get_developer_repo_root)


type WorkflowPatcher = Callable[[pytest.MonkeyPatch, Path], None]


@pytest.mark.parametrize(
    ("command_name", "workflow_module", "workflow_patcher", "extra_args"),
    [
        ("update-docs", update_docs, _patch_docs_workflow, []),
        ("update-test", update_test, _patch_test_workflow, []),
        ("update-logic", update_logic, _patch_logic_workflow, []),
        ("update-installer", update_installer, _patch_installer_workflow, ["--context", "entry-a", "--prompt", "prompt-a"]),
    ],
)
def test_workflow_commands_forward_run_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command_name: str,
    workflow_module: object,
    workflow_patcher: WorkflowPatcher,
    extra_args: list[str],
) -> None:
    _prepare_fake_repo_root(tmp_path=tmp_path)
    workflow_patcher(monkeypatch, tmp_path)
    captured_runs: list[bool] = []

    def fake_agents_create_impl(**kwargs: object) -> None:
        run_value = kwargs.get("run")
        assert isinstance(run_value, bool)
        captured_runs.append(run_value)

    monkeypatch.setattr(workflow_module, "agents_create_impl", fake_agents_create_impl)

    result = CliRunner().invoke(get_app(), [command_name, "--run", *extra_args])

    assert result.exit_code == 0
    assert captured_runs == [True]
