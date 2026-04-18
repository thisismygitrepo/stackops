from __future__ import annotations

import json
from pathlib import Path

from stackops.utils.schemas.layouts import layout_types as layout_types_module


def test_serialize_layouts_to_file_creates_schema_annotated_json(tmp_path: Path) -> None:
    layout_path = tmp_path / "configs" / "layout.json"
    layouts: list[layout_types_module.LayoutConfig] = [
        {"layoutName": "main", "layoutTabs": [{"tabName": "shell", "startDir": "~/work", "command": "bash"}]}
    ]

    layout_types_module.serialize_layouts_to_file(layouts=layouts, version="0.1", path=layout_path.as_posix())

    content = json.loads(layout_path.read_text(encoding="utf-8"))
    assert content == {"$schema": "https://bit.ly/cfglayout", "version": "0.1", "layouts": layouts}


def test_serialize_layouts_to_file_replaces_matching_layout_and_appends_new_one(tmp_path: Path) -> None:
    layout_path = tmp_path / "configs" / "layout.json"
    original_layouts: list[layout_types_module.LayoutConfig] = [
        {"layoutName": "main", "layoutTabs": [{"tabName": "shell", "startDir": "/tmp", "command": "bash"}]}
    ]
    updated_layouts: list[layout_types_module.LayoutConfig] = [
        {"layoutName": "main", "layoutTabs": [{"tabName": "editor", "startDir": "/work", "command": "nvim"}]},
        {"layoutName": "secondary", "layoutTabs": [{"tabName": "logs", "startDir": "/var/log", "command": "tail -f syslog"}]},
    ]

    layout_types_module.serialize_layouts_to_file(layouts=original_layouts, version="0.1", path=layout_path.as_posix())
    layout_types_module.serialize_layouts_to_file(layouts=updated_layouts, version="0.1", path=layout_path.as_posix())

    content = json.loads(layout_path.read_text(encoding="utf-8"))
    assert content["layouts"] == updated_layouts
    assert content["$schema"] == "https://bit.ly/cfglayout"


def test_substitute_home_expands_tab_paths_and_shorthand_commands() -> None:
    home = Path.home()
    tabs: list[layout_types_module.TabConfig] = [
        {"tabName": "fire", "startDir": "~/work", "command": "f launch"},
        {"tabName": "seek", "startDir": "$HOME/research", "command": "s query", "tabWeight": 2},
        {"tabName": "term", "startDir": "/tmp", "command": "t shell"},
    ]

    substituted = layout_types_module.substitute_home(tabs)

    assert substituted == [
        {"tabName": "fire", "startDir": f"{home}/work", "command": "~/.config/stackops/scripts/wrap_mcfg fire launch"},
        {"tabName": "seek", "startDir": f"{home}/research", "command": "~/.config/stackops/scripts/wrap_mcfg seek query", "tabWeight": 2},
        {"tabName": "term", "startDir": "/tmp", "command": "~/.config/stackops/scripts/wrap_mcfg terminal shell"},
    ]
