from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

import yaml

from stackops.utils.schemas.layouts.layout_file import read_layouts_file
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, PaneConfig, TabConfig
from stackops.utils.schemas.yaml_schema import JsonValue

type LayoutSwitchFailureReason = Literal["invalid_file", "entry_gone", "unsupported_format"]


# The layout, or one of its tabs, or one pane of that tab. A tab is named by where it stands and by its name, since two tabs of a layout
# may share a name; the name is there to notice a file that changed since it was read.
@dataclass(frozen=True)
class LayoutSwitchTarget:
    layout_name: str
    tab_index: int | None
    tab_name: str | None
    pane_name: str | None


@dataclass(frozen=True)
class LayoutSwitchFailure:
    reason: LayoutSwitchFailureReason
    message: str


# Switches one entry of a layout file on or off by changing its `enabled` value where it is written, or by writing `enabled: false` as the
# entry's first key. Nothing else in the file is touched, so comments and the way it is laid out stay. The changed text is read back before
# it is saved, and is only saved when it says what the file said before plus this one switch.
def switch_layout_entry(path: Path, target: LayoutSwitchTarget, enabled: bool) -> LayoutSwitchFailure | None:
    try:
        layouts_file = read_layouts_file(path=path)
    except (OSError, ValueError) as error:
        return LayoutSwitchFailure(reason="invalid_file", message=str(error))
    gone = LayoutSwitchFailure(reason="entry_gone", message=f"""{path.name} has changed since it was read, and that entry is no longer where it was. Refresh the list.""")
    layouts = layouts_file["layouts"]
    layout_index = next((index for index, layout in enumerate(layouts) if layout["layoutName"] == target.layout_name), None)
    if layout_index is None:
        return gone
    entry: LayoutConfig | TabConfig | PaneConfig = layouts[layout_index]
    steps: list[tuple[str, int]] = [("layouts", layout_index)]
    if target.tab_index is not None:
        tabs = layouts[layout_index]["layoutTabs"]
        if target.tab_index >= len(tabs) or tabs[target.tab_index]["tabName"] != target.tab_name:
            return gone
        tab = tabs[target.tab_index]
        entry = tab
        steps.append(("layoutTabs", target.tab_index))
        if target.pane_name is not None:
            pane_index = next((index for index, pane in enumerate(tab["panes"]) if pane["paneName"] == target.pane_name), None)
            if pane_index is None:
                return gone
            entry = tab["panes"][pane_index]
            steps.append(("panes", pane_index))
    if entry.get("enabled", True) == enabled:
        return None

    text = path.read_text(encoding="utf-8", newline="")
    node = cast(yaml.MappingNode, yaml.compose(text, Loader=yaml.SafeLoader))
    for key, index in steps:
        sequence = next(value_node for key_node, value_node in node.value if key_node.value == key)
        node = sequence.value[index]
    word = "true" if enabled else "false"
    written = next((value_node for key_node, value_node in node.value if key_node.value == "enabled"), None)
    if written is not None:
        changed_text = f"""{text[: written.start_mark.index]}{word}{text[written.end_mark.index :]}"""
    else:
        first_key = node.value[0][0].start_mark
        addition = f"""enabled: {word}, """ if node.flow_style else f"""enabled: {word}\n{" " * first_key.column}"""
        changed_text = f"""{text[: first_key.index]}{addition}{text[first_key.index :]}"""

    entry["enabled"] = enabled
    try:
        said = cast(JsonValue, yaml.load(changed_text, Loader=yaml.CSafeLoader))
    except yaml.YAMLError:
        said = None
    if said != layouts_file:
        return LayoutSwitchFailure(
            reason="unsupported_format",
            message=f"""{path.name} is written in a way this switch cannot change safely. Open it and {"remove the entry's `enabled: false`" if enabled else "add `enabled: false` to the entry"} by hand.""",
        )
    path.write_text(changed_text, encoding="utf-8", newline="")
    return None
