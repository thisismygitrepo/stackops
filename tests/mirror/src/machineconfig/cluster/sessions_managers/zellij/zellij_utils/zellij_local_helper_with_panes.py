from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.cluster.sessions_managers.zellij.zellij_utils import zellij_local_helper_with_panes as subject
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def _make_tabs() -> list[TabConfig]:
    return [
        {"tabName": "Bot Alpha", "startDir": "/repo/a", "command": "python bot_a.py"},
        {"tabName": "Bot Beta", "startDir": "/repo/a", "command": "python bot_b.py"},
        {"tabName": "Logs", "startDir": "/repo/logs", "command": "tail -f app.log"},
    ]


def _make_layout_config() -> LayoutConfig:
    return {"layoutName": "Grouped", "layoutTabs": _make_tabs()}


def test_create_tab_with_panes_uses_split_container_for_multiple_commands() -> None:
    section = subject.create_tab_with_panes(_make_tabs()[:2], tab_name="Bots", common_cwd="/repo/a", split_direction="horizontal")

    assert 'tab name="Bots" cwd="/repo/a"' in section
    assert 'pane split_direction="horizontal"' in section
    assert section.count('pane command="python"') == 2


def test_generate_tab_name_handles_single_and_grouped_tabs() -> None:
    tabs = _make_tabs()

    assert subject.generate_tab_name([tabs[0]], 1) == "Bot Alpha"
    assert subject.generate_tab_name(tabs[:2], 2) == "Bot×2"


def test_create_zellij_layout_with_panes_writes_absolute_kdl_file(tmp_path: Path) -> None:
    output_path = tmp_path.joinpath("grouped.kdl")

    created_path = subject.create_zellij_layout_with_panes(
        layout_config=_make_layout_config(), output_path=str(output_path), panes_per_tab=2, split_direction="vertical"
    )

    content = output_path.read_text(encoding="utf-8")
    assert created_path == str(output_path.absolute())
    assert content.count("  tab name=") == 2
    assert 'pane split_direction="vertical"' in content
    assert 'tab name="Logs" cwd="/repo/logs"' in content


def test_create_zellij_layout_with_panes_rejects_invalid_output_path(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must end with .kdl"):
        subject.create_zellij_layout_with_panes(
            layout_config=_make_layout_config(), output_path=str(tmp_path.joinpath("grouped.txt")), panes_per_tab=1, split_direction="vertical"
        )
