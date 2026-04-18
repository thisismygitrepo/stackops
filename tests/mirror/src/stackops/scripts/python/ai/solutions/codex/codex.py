from __future__ import annotations

from pathlib import Path

import pytest

from stackops.scripts.python.ai.solutions.codex import codex as codex_module


def test_build_configuration_creates_private_config_template(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    codex_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=False)

    config_path = repo_root / ".codex" / "config.toml"
    expected = codex_module.PRIVATE_CONFIG_TEMPLATE_PATH.read_text(encoding="utf-8")

    assert config_path.read_text(encoding="utf-8") == expected


def test_build_configuration_preserves_existing_private_config(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    codex_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=False)

    config_path = repo_root / ".codex" / "config.toml"
    config_path.write_text("sentinel\n", encoding="utf-8")

    codex_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=False)

    assert config_path.read_text(encoding="utf-8") == "sentinel\n"


def test_build_configuration_writes_agents_file_when_requested(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    instructions_path = tmp_path / "instructions.md"
    instructions_path.write_text("codex rules\n", encoding="utf-8")

    monkeypatch.setattr(codex_module, "get_generic_instructions_path", lambda: instructions_path)

    codex_module.build_configuration(repo_root=repo_root, add_private_config=False, add_instructions=True)

    assert (repo_root / "AGENTS.md").read_text(encoding="utf-8") == "codex rules\n"
    assert (repo_root / ".codex").exists() is False
