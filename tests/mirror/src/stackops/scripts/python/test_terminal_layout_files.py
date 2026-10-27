from pathlib import Path
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.scripts.python.terminal_layout_files import resolve_layout_file
from stackops.utils import managed_file_cli
from stackops.utils.repos import stackops_paths


@pytest.mark.parametrize("command", ("path", "init", "validate"))
@pytest.mark.parametrize("source", ("project", "p", "user", "u"))
def test_explicit_layout_file_overrides_source(
    command: str, source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout_path = tmp_path / "custom.json"
    source_lookup = Mock(side_effect=AssertionError("Explicit layout files must bypass project lookup"))
    monkeypatch.setattr(stackops_paths, "require_current_repo_stackops_path", source_lookup)
    managed_action = Mock()
    monkeypatch.setattr(managed_file_cli, "run_managed_file_action", managed_action)

    result = CliRunner().invoke(terminal.get_app(), [command, str(layout_path), "--source", source])

    assert result.exit_code == 0, result.output
    managed_action.assert_called_once_with(kind="layouts", action=command, path=layout_path)
    source_lookup.assert_not_called()


def test_project_layout_from_nested_directory_uses_repository_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from git import Repo

    with Repo.init(tmp_path):
        nested_directory = tmp_path / "src" / "nested"
        nested_directory.mkdir(parents=True)
        monkeypatch.chdir(nested_directory)
        layout_path = resolve_layout_file(layouts_file=None, source="p")

    assert layout_path == tmp_path / ".stackops" / "config" / "layout.json"
