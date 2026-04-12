from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.codex.codex_privacy as codex_privacy


def _patch_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setattr(codex_privacy.pathlib.Path, "home", lambda: home)


def test_secure_codex_configs_writes_global_and_repo_configs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    workspace.joinpath(".codex").mkdir(parents=True)

    _patch_home(monkeypatch=monkeypatch, home=home)
    monkeypatch.chdir(workspace)

    chmod_calls: list[Path] = []
    monkeypatch.setattr(codex_privacy.os, "chmod", lambda path, mode: chmod_calls.append(Path(path)))

    codex_privacy.secure_codex_configs()

    global_config = home / ".codex" / "config.toml"
    local_config = workspace / ".codex" / "config.toml"
    global_text = global_config.read_text(encoding="utf-8")
    assert global_config.is_file()
    assert local_config.is_file()
    assert global_text == local_config.read_text(encoding="utf-8")
    assert "[analytics]" in global_text
    assert 'persistence = "none"' in global_text
    assert chmod_calls == [global_config, local_config]


def test_secure_codex_configs_skips_repo_config_without_existing_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True)

    _patch_home(monkeypatch=monkeypatch, home=home)
    monkeypatch.chdir(workspace)

    codex_privacy.secure_codex_configs()

    assert (home / ".codex" / "config.toml").is_file()
    assert not (workspace / ".codex" / "config.toml").exists()
