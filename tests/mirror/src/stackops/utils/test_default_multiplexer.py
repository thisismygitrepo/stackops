import json
from pathlib import Path

import pytest

import stackops.utils.schemas.config as config_assets
from stackops.utils import default_multiplexer, source_of_truth
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.config.multiplexer_types import AGENT_MULTIPLEXERS, SESSION_MULTIPLEXERS


@pytest.fixture
def config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "config.json"
    monkeypatch.setattr(source_of_truth, "DOTFILES_STACKOPS_CONFIG_PATH", path)
    monkeypatch.setattr(default_multiplexer, "DOTFILES_STACKOPS_CONFIG_PATH", path)
    return path


def test_schema_enums_match_multiplexer_literals() -> None:
    schema_path = get_path_reference_path(module=config_assets, path_reference=config_assets.CONFIG_SCHEMA_PATH_REFERENCE)
    schema: dict[str, dict[str, dict[str, list[str]]]] = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["properties"]["default_session_multiplexer"]["enum"] == list(SESSION_MULTIPLEXERS)
    assert schema["properties"]["default_agent_multiplexer"]["enum"] == list(AGENT_MULTIPLEXERS)


def test_explicit_multiplexer_wins_over_config(config_path: Path) -> None:
    config_path.write_text("""{"version": "1.0.0", "default_session_multiplexer": "tuios", "default_agent_multiplexer": "herdr"}""", encoding="utf-8")
    assert default_multiplexer.resolve_session_multiplexer(multiplexer="t") == "tmux"
    assert default_multiplexer.resolve_agent_multiplexer(multiplexer="aoe") == "aoe"


def test_config_default_multiplexer_is_used(config_path: Path) -> None:
    config_path.write_text("""{"version": "1.0.0", "default_session_multiplexer": "tuios", "default_agent_multiplexer": "herdr"}""", encoding="utf-8")
    assert default_multiplexer.resolve_session_multiplexer(multiplexer=None) == "tuios"
    assert default_multiplexer.resolve_agent_multiplexer(multiplexer=None) == "herdr"


def test_builtin_default_when_config_missing_or_key_absent(config_path: Path) -> None:
    assert default_multiplexer.resolve_session_multiplexer(multiplexer=None) == "tmux"
    assert default_multiplexer.resolve_agent_multiplexer(multiplexer=None) == "tuios"
    config_path.write_text("""{"version": "1.0.0"}""", encoding="utf-8")
    assert default_multiplexer.resolve_session_multiplexer(multiplexer=None) == "tmux"
    assert default_multiplexer.resolve_agent_multiplexer(multiplexer=None) == "tuios"


def test_agent_multiplexer_rejects_session_only_value(config_path: Path) -> None:
    config_path.write_text("""{"version": "1.0.0", "default_agent_multiplexer": "tmux"}""", encoding="utf-8")
    with pytest.raises(ValueError, match="default_agent_multiplexer 'tmux' must be one of tuios, herdr, aoe"):
        default_multiplexer.resolve_agent_multiplexer(multiplexer=None)
