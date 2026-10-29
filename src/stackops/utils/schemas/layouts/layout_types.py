#!/usr/bin/env python3
"""
Type definitions for the standardized layout configuration schema.
This module defines the data structures that match the layout.yaml schema.
"""

from pathlib import Path
import json
from typing import Literal, NotRequired, TypedDict, cast


type TabArrangement = Literal["columns", "rows", "grid"]
type LayoutFileVersion = Literal["0.2"]


class PaneConfig(TypedDict):
    """Configuration for a single pane in a tab."""
    paneName: str
    startDir: str
    command: str


class TabConfig(TypedDict):
    """Configuration for a single tab in a layout, holding one or more panes."""
    tabName: str
    panes: list[PaneConfig]
    arrangement: NotRequired[TabArrangement]
    tabWeight: NotRequired[int]


def single_pane_tab(*, tab_name: str, start_dir: str, command: str) -> TabConfig:
    return {"tabName": tab_name, "panes": [{"paneName": tab_name, "startDir": start_dir, "command": command}]}


class LayoutConfig(TypedDict):
    """Configuration for a complete layout with its tabs."""
    layoutName: str
    layoutTabs: list[TabConfig]


class LayoutsFile(TypedDict):
    """Complete layout file structure."""
    version: LayoutFileVersion
    layouts: list[LayoutConfig]


def substitute_home(tabs: list[TabConfig]) -> list["TabConfig"]:
    json_str = json.dumps(tabs)
    json_str = json_str.replace("~", str(Path.home())).replace("$HOME", str(Path.home()))
    json_str = json_str.replace("""command": "f """, """command": "~/.config/stackops/scripts/wrap_stackops fire """)
    json_str = json_str.replace("""command": "t """, """command": "~/.config/stackops/scripts/wrap_stackops terminal """)
    json_str = json_str.replace("""command": "s """, """command": "~/.config/stackops/scripts/wrap_stackops seek """)
    return cast(list[TabConfig], json.loads(json_str))
