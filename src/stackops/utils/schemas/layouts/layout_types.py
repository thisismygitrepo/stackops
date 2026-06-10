#!/usr/bin/env python3
"""
Type definitions for the standardized layout configuration schema.
This module defines the data structures that match the layout.json schema.
"""

from pathlib import Path
import json
from typing import Literal, NotRequired, TypeAlias, TypedDict, cast

LayoutFileWriteMode: TypeAlias = Literal["replace_file", "merge_by_layout_name"]


class TabConfig(TypedDict):
    """Configuration for a single tab in a layout."""
    tabName: str
    startDir: str
    command: str
    tabWeight: NotRequired[int]


class LayoutConfig(TypedDict):
    """Configuration for a complete layout with its tabs."""
    layoutName: str
    layoutTabs: list[TabConfig]


class LayoutsFile(TypedDict):
    """Complete layout file structure."""
    version: str
    layouts: list[LayoutConfig]


LayoutJsonFile = TypedDict(
    "LayoutJsonFile",
    {
        "$schema": str,
        "version": str,
        "layouts": list[LayoutConfig],
    },
)


def _get_unique_layout_indexes_by_name(layouts: list[LayoutConfig], source: str) -> dict[str, int]:
    layout_indexes: dict[str, int] = {}
    for layout_index, layout_config in enumerate(layouts):
        layout_name = layout_config["layoutName"]
        if layout_name in layout_indexes:
            raise ValueError(f"Duplicate layoutName {layout_name!r} in {source}")
        layout_indexes[layout_name] = layout_index
    return layout_indexes


def _merge_layouts_by_name(existing_layouts: list[LayoutConfig], new_layouts: list[LayoutConfig]) -> list[LayoutConfig]:
    merged_layouts = list(existing_layouts)
    layout_indexes = _get_unique_layout_indexes_by_name(layouts=merged_layouts, source="existing layout file")
    _get_unique_layout_indexes_by_name(layouts=new_layouts, source="new layouts")
    for new_layout in new_layouts:
        new_layout_name = new_layout["layoutName"]
        existing_index = layout_indexes.get(new_layout_name)
        if existing_index is None:
            layout_indexes[new_layout_name] = len(merged_layouts)
            merged_layouts.append(new_layout)
        else:
            merged_layouts[existing_index] = new_layout
    return merged_layouts


def serialize_layouts_to_file(layouts: list[LayoutConfig], version: Literal["0.1"], path: str, *, write_mode: LayoutFileWriteMode) -> None:
    _get_unique_layout_indexes_by_name(layouts=layouts, source="new layouts")
    layout_file: LayoutJsonFile = {
        "$schema": "https://bit.ly/cfglayout",
        "version": version,
        "layouts": layouts,
    }
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    match write_mode:
        case "replace_file":
            pass
        case "merge_by_layout_name":
            if p.exists():
                existing_layout_file = cast(LayoutsFile, json.loads(p.read_text(encoding="utf-8")))
                layout_file["layouts"] = _merge_layouts_by_name(existing_layouts=existing_layout_file["layouts"], new_layouts=layouts)
    p.write_text(json.dumps(layout_file, indent=4), encoding="utf-8")


def substitute_home(tabs: list[TabConfig]) -> list["TabConfig"]:
    json_str = json.dumps(tabs)
    json_str = json_str.replace("~", str(Path.home())).replace("$HOME", str(Path.home()))
    json_str = json_str.replace("""command": "f """, """command": "~/.config/stackops/scripts/wrap_stackops fire """)
    json_str = json_str.replace("""command": "t """, """command": "~/.config/stackops/scripts/wrap_stackops terminal """)
    json_str = json_str.replace("""command": "s """, """command": "~/.config/stackops/scripts/wrap_stackops seek """)
    return cast(list[TabConfig], json.loads(json_str))
