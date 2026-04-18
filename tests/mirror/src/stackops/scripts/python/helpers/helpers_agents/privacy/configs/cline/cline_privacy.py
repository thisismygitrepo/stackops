from __future__ import annotations

import json
from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline.cline_privacy as cline_privacy


def _patch_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setattr(cline_privacy.Path, "home", lambda: home)


def _config_paths(home: Path) -> tuple[Path, ...]:
    vscode_storage = home / ".config" / "Code" / "User" / "globalStorage" / "saoudrizwan.cline"
    return (
        home / ".cline" / "settings.json",
        home / ".cline" / "config.json",
        home / ".config" / "cline" / "settings.json",
        vscode_storage / "settings.json",
        vscode_storage / "settings" / "settings.json",
    )


def test_secure_cline_config_writes_all_known_locations(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    _patch_home(monkeypatch=monkeypatch, home=home)
    config_paths = _config_paths(home=home)

    config_paths[0].parent.mkdir(parents=True, exist_ok=True)
    config_paths[0].write_text("""{"keep": "value"}""", encoding="utf-8")
    config_paths[1].parent.mkdir(parents=True, exist_ok=True)
    config_paths[1].write_text("""{broken json""", encoding="utf-8")

    chmod_calls: list[Path] = []
    monkeypatch.setattr(cline_privacy.os, "chmod", lambda path, mode: chmod_calls.append(Path(path)))

    cline_privacy.secure_cline_config()

    for config_path in config_paths:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["telemetry"] is False
        assert data["disableTelemetry"] is True
        assert data["disableCaching"] is True
        assert data["recordHistory"] is False

    assert json.loads(config_paths[0].read_text(encoding="utf-8"))["keep"] == "value"
    assert "keep" not in json.loads(config_paths[1].read_text(encoding="utf-8"))
    assert chmod_calls == list(config_paths)


def test_secure_cline_config_ignores_chmod_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    _patch_home(monkeypatch=monkeypatch, home=home)
    monkeypatch.setattr(cline_privacy.os, "chmod", lambda path, mode: (_ for _ in ()).throw(PermissionError(str(path))))

    cline_privacy.secure_cline_config()

    for config_path in _config_paths(home=home):
        assert config_path.is_file()
