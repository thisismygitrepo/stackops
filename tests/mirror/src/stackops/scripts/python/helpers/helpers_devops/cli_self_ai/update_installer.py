from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_installer as update_installer_module


def test_get_update_installer_prompt_mentions_resolved_target_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    expected_relative_path = Path("src", "stackops", "jobs", "installer", "installer_data.json")
    monkeypatch.setattr(update_installer_module, "get_developer_repo_root", lambda: tmp_path)
    monkeypatch.setattr(update_installer_module, "_get_installer_data_repo_relative_path", lambda: expected_relative_path)
    get_prompt = cast(Callable[[], str], getattr(update_installer_module, "_get_update_installer_prompt"))

    prompt = get_prompt()

    assert str(tmp_path.joinpath(expected_relative_path)) in prompt
    assert "don't touch any other field other than thee file pattern" in prompt


def test_update_installer_uses_default_prompt_and_context_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    repo_root.joinpath("pyproject.toml").write_text("", encoding="utf-8")
    relative_path = Path("src", "stackops", "jobs", "installer", "installer_data.json")
    captured: dict[str, object] = {}

    def fake_agents_create_impl(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(update_installer_module, "get_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr(update_installer_module, "_get_installer_data_repo_relative_path", lambda: relative_path)
    monkeypatch.setattr(update_installer_module, "agents_create_impl", fake_agents_create_impl)

    update_installer_module.update_installer()

    get_prompt = cast(Callable[[], str], getattr(update_installer_module, "_get_update_installer_prompt"))

    assert captured["context"] is None
    assert captured["context_path"] == str(repo_root.joinpath(relative_path))
    assert captured["prompt"] == get_prompt()
    assert captured["output_path"] == str(
        repo_root.joinpath(".ai", "agents", update_installer_module.DEFAULT_INSTALLER_JOB_NAME, "layout.json")
    )
