from pathlib import Path
from typing import Literal
from unittest.mock import Mock

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents_config_files
from stackops.utils import managed_agent_files
from stackops.utils.managed_agent_files import AgentManagedFileSource
from stackops.utils.managed_files import ManagedFileKind


@pytest.mark.parametrize("action", ("path", "init", "validate"))
@pytest.mark.parametrize(("alias", "source"), (("w", "workspace"), ("u", "user"), ("l", "library")))
def test_config_source_aliases_resolve_to_canonical_paths(
    action: str, alias: str, source: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    locations: tuple[tuple[AgentManagedFileSource, Path], ...] = (
        ("workspace", tmp_path / "workspace.yaml"),
        ("user", tmp_path / "user.yaml"),
        ("library", tmp_path / "library.yaml"),
    )
    monkeypatch.setattr(managed_agent_files, "agent_managed_file_locations", Mock(return_value=locations))
    captured_actions: list[tuple[ManagedFileKind, str, Path | None]] = []

    def capture_action(*, kind: ManagedFileKind, action: Literal["path", "init", "validate"], path: Path | None) -> None:
        assert kind == "prompts"
        captured_actions.append((kind, action, path))

    monkeypatch.setattr(agents_config_files, "run_managed_file_action", capture_action)
    result = CliRunner().invoke(agents_config_files.get_app(), [action, "prompts", "--source", alias])

    assert result.exit_code == 0, result.output
    assert captured_actions == [("prompts", action, tmp_path / f"""{source}.yaml""")]


@pytest.mark.parametrize("action", ("path", "init", "validate"))
def test_config_custom_path_overrides_source(action: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom_path = tmp_path / "custom.yaml"
    source_lookup = Mock(side_effect=AssertionError("Custom files must bypass source lookup"))
    monkeypatch.setattr(agents_config_files, "resolve_agent_managed_file_path", source_lookup)
    managed_action = Mock()
    monkeypatch.setattr(agents_config_files, "run_managed_file_action", managed_action)

    result = CliRunner().invoke(
        agents_config_files.get_app(), [action, "prompts", "--source", "user", "--custom-path", str(custom_path)],
    )

    assert result.exit_code == 0, result.output
    managed_action.assert_called_once_with(kind="prompts", action=action, path=custom_path)
    source_lookup.assert_not_called()
