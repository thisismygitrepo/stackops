import json
from pathlib import Path
from typing import get_args

import pytest

import stackops.utils.schemas.config as config_assets
from stackops.utils import default_agent, source_of_truth
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


@pytest.fixture
def config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    monkeypatch.setattr(source_of_truth, "DOTFILES_STACKOPS_CONFIG_PATH", path)
    monkeypatch.setattr(default_agent, "DOTFILES_STACKOPS_CONFIG_PATH", path)
    return path


def test_schema_enum_matches_agents_literal() -> None:
    schema_path = get_path_reference_path(module=config_assets, path_reference=config_assets.CONFIG_SCHEMA_PATH_REFERENCE)
    schema: dict[str, dict[str, dict[str, list[str]]]] = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["default_agent"]["enum"] == list(get_args(AGENTS))


def test_explicit_agent_wins_over_config(config_path: Path) -> None:
    config_path.write_text("""{"version": "1.0.0", "default_agent": "claude"}""", encoding="utf-8")
    assert default_agent.resolve_agent(agent="pi") == "pi"


def test_config_default_agent_is_used(config_path: Path) -> None:
    config_path.write_text("""{"version": "1.0.0", "default_agent": "claude"}""", encoding="utf-8")
    assert default_agent.resolve_agent(agent=None) == "claude"


def test_builtin_default_when_config_missing_or_key_absent(config_path: Path) -> None:
    assert default_agent.resolve_agent(agent=None) == "codex"
    config_path.write_text("""{"version": "1.0.0"}""", encoding="utf-8")
    assert default_agent.resolve_agent(agent=None) == "codex"


def test_invalid_default_agent_is_rejected(config_path: Path) -> None:
    config_path.write_text("""{"version": "1.0.0", "default_agent": "claud"}""", encoding="utf-8")
    with pytest.raises(ValueError, match="default_agent 'claud' must be one of"):
        default_agent.resolve_agent(agent=None)
