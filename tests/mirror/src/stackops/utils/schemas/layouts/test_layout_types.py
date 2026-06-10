import json
from pathlib import Path
from typing import cast

from stackops.utils.schemas.layouts.layout_types import LayoutConfig, LayoutJsonFile, TabConfig, serialize_layouts_to_file


def test_serialize_layouts_to_file_replace_file_drops_existing_layouts(tmp_path: Path) -> None:
    stale_tab: TabConfig = {"tabName": "stale-tab", "startDir": "$HOME", "command": "echo stale"}
    fresh_tab: TabConfig = {"tabName": "fresh-tab", "startDir": "$HOME", "command": "echo fresh"}
    stale_layout: LayoutConfig = {"layoutName": "stale-layout", "layoutTabs": [stale_tab]}
    fresh_layout: LayoutConfig = {"layoutName": "fresh-layout", "layoutTabs": [fresh_tab]}
    layout_path = tmp_path.joinpath("layout.json")

    serialize_layouts_to_file(layouts=[stale_layout], version="0.1", path=str(layout_path), write_mode="replace_file")
    serialize_layouts_to_file(layouts=[fresh_layout], version="0.1", path=str(layout_path), write_mode="replace_file")

    saved_layout_file = cast(LayoutJsonFile, json.loads(layout_path.read_text(encoding="utf-8")))
    assert saved_layout_file["layouts"] == [fresh_layout]


def test_serialize_layouts_to_file_merge_by_layout_name_replaces_matching_layouts(tmp_path: Path) -> None:
    original_tab: TabConfig = {"tabName": "original-tab", "startDir": "$HOME", "command": "echo original"}
    unchanged_tab: TabConfig = {"tabName": "unchanged-tab", "startDir": "$HOME", "command": "echo unchanged"}
    replacement_tab: TabConfig = {"tabName": "replacement-tab", "startDir": "$HOME", "command": "echo replacement"}
    appended_tab: TabConfig = {"tabName": "appended-tab", "startDir": "$HOME", "command": "echo appended"}
    original_layout: LayoutConfig = {"layoutName": "same-layout", "layoutTabs": [original_tab]}
    unchanged_layout: LayoutConfig = {"layoutName": "unchanged-layout", "layoutTabs": [unchanged_tab]}
    replacement_layout: LayoutConfig = {"layoutName": "same-layout", "layoutTabs": [replacement_tab]}
    appended_layout: LayoutConfig = {"layoutName": "appended-layout", "layoutTabs": [appended_tab]}
    layout_path = tmp_path.joinpath("layout.json")

    serialize_layouts_to_file(layouts=[original_layout, unchanged_layout], version="0.1", path=str(layout_path), write_mode="replace_file")
    serialize_layouts_to_file(layouts=[replacement_layout, appended_layout], version="0.1", path=str(layout_path), write_mode="merge_by_layout_name")

    saved_layout_file = cast(LayoutJsonFile, json.loads(layout_path.read_text(encoding="utf-8")))
    assert saved_layout_file["layouts"] == [replacement_layout, unchanged_layout, appended_layout]
