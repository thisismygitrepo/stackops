from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.cluster.sessions_managers.helpers.enhanced_command_runner as enhanced_command_runner
import machineconfig.cluster.sessions_managers.zellij.zellij_local as zellij_local
from machineconfig.cluster.sessions_managers.zellij.zellij_local import (
    ZellijLayoutGenerator,
)
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def _build_layout_config() -> LayoutConfig:
    return {
        "layoutName": "demo",
        "layoutTabs": [
            {
                "tabName": "api",
                "startDir": "~/code/api",
                "command": "uv run api.py",
            },
            {
                "tabName": "worker",
                "startDir": "~/code/worker",
                "command": "uv run worker.py",
            },
        ],
    }


def test_create_zellij_layout_uses_copy_of_input_tabs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layout_config = _build_layout_config()
    emitted_sections: list[str] = []

    def fake_validate_layout_config(candidate: LayoutConfig) -> None:
        assert candidate["layoutName"] == "demo"

    def fake_create_tab_section(tab: TabConfig) -> str:
        tab["tabName"] = "mutated"
        section = f"tab {tab['command']}"
        emitted_sections.append(section)
        return section

    monkeypatch.setattr(zellij_local, "validate_layout_config", fake_validate_layout_config)
    monkeypatch.setattr(zellij_local, "create_tab_section", fake_create_tab_section)
    monkeypatch.setattr(zellij_local.console, "print", lambda *args, **kwargs: None)

    result = zellij_local.create_zellij_layout(layout_config, layout_template="layout {")

    assert layout_config["layoutTabs"][0]["tabName"] == "api"
    assert emitted_sections == ["tab uv run api.py", "tab uv run worker.py"]
    assert result == "layout {\ntab uv run api.py\ntab uv run worker.py\n}\n"


def test_create_layout_file_writes_generated_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_home() -> Path:
        return tmp_path

    monkeypatch.setattr(zellij_local.Path, "home", staticmethod(fake_home))
    monkeypatch.setattr(zellij_local, "create_zellij_layout", lambda layout_config, layout_template: "layout-content")
    monkeypatch.setattr(zellij_local.console, "print", lambda *args, **kwargs: None)

    generator = ZellijLayoutGenerator(layout_config=_build_layout_config(), session_name="alpha")

    created = generator.create_layout_file()
    assert created is True
    assert generator.layout_path is not None
    layout_path = Path(generator.layout_path)
    assert layout_path.read_text(encoding="utf-8") == "layout-content"
    assert layout_path.parent == tmp_path / "tmp_results" / "sessions" / "zellij_layouts"


def test_run_updates_session_name_from_helper_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_start(
        *,
        session_name: str,
        layout_path: str,
        on_conflict: str,
    ) -> dict[str, str | bool]:
        assert session_name == "alpha"
        assert layout_path == "/tmp/layout.kdl"
        assert on_conflict == "error"
        return {"success": True, "session_name": "alpha_renamed"}

    monkeypatch.setattr(
        enhanced_command_runner,
        "enhanced_zellij_session_start",
        fake_start,
    )

    generator = ZellijLayoutGenerator(layout_config=_build_layout_config(), session_name="alpha")
    generator.layout_path = "/tmp/layout.kdl"

    generator.run(on_conflict="error")

    assert generator.session_name == "alpha_renamed"


def test_run_command_in_zellij_tab_includes_cwd_only_when_present() -> None:
    with_cwd = zellij_local.run_command_in_zellij_tab(
        command="echo hi",
        tab_name="api",
        cwd="/tmp/work",
    )
    without_cwd = zellij_local.run_command_in_zellij_tab(
        command="echo hi",
        tab_name="api",
        cwd=None,
    )

    assert "--cwd /tmp/work" in with_cwd
    assert "--cwd" not in without_cwd
