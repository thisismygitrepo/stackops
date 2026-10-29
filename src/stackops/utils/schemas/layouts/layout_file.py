from collections.abc import Mapping
from pathlib import Path
from typing import Literal, TypeAlias, cast

import yaml

from stackops.utils.schemas.layouts.layout_constants import LAYOUT_FILE_SUFFIX, LAYOUT_SCHEMA_URL
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, LayoutsFile
from stackops.utils.schemas.yaml_schema import JsonValue

LayoutFileWriteMode: TypeAlias = Literal["replace_file", "merge_by_layout_name"]


class _LayoutYamlDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: object) -> bool:
        return True


def _require_layout_suffix(path: Path) -> None:
    if path.suffix != LAYOUT_FILE_SUFFIX:
        raise ValueError(f"""Layout files must be YAML with the '{LAYOUT_FILE_SUFFIX}' suffix: {path}""")


def layout_yaml_text(document: Mapping[str, object]) -> str:
    return yaml.dump(document, Dumper=_LayoutYamlDumper, sort_keys=False, default_flow_style=False, allow_unicode=True, width=float("inf"))


def read_layouts_file(path: Path) -> LayoutsFile:
    _require_layout_suffix(path)
    try:
        document = cast(JsonValue, yaml.safe_load(path.read_text(encoding="utf-8")))
    except yaml.YAMLError as error:
        raise ValueError(f"""Invalid YAML in layout file '{path}': {error}""") from error
    if not isinstance(document, dict):
        raise ValueError(f"""Invalid layout file '{path}': expected a mapping at the top level.""")
    if not isinstance(document.get("version"), str):
        raise ValueError(f"""Invalid layout file '{path}': 'version' must be a quoted string, e.g. version: "0.1".""")
    raw_layouts = document.get("layouts")
    if not isinstance(raw_layouts, list):
        raise ValueError(f"""Invalid layout file '{path}': 'layouts' must be a list.""")
    for layout_index, layout in enumerate(raw_layouts):
        location = f"""'{path}' at layouts[{layout_index}]"""
        if not isinstance(layout, dict):
            raise ValueError(f"""Invalid layout in {location}: expected a mapping.""")
        if not isinstance(layout.get("layoutName"), str):
            raise ValueError(f"""Invalid layout in {location}: 'layoutName' must be a string.""")
        tabs = layout.get("layoutTabs")
        if not isinstance(tabs, list):
            raise ValueError(f"""Invalid layout in {location}: 'layoutTabs' must be a list.""")
        for tab_index, tab in enumerate(tabs):
            tab_location = f"""{location}.layoutTabs[{tab_index}]"""
            if not isinstance(tab, dict):
                raise ValueError(f"""Invalid tab in {tab_location}: expected a mapping.""")
            if not isinstance(tab.get("tabName"), str):
                raise ValueError(f"""Invalid tab in {tab_location}: 'tabName' must be a string.""")
            if tab.get("arrangement", "grid") not in ("columns", "rows", "grid"):
                raise ValueError(f"""Invalid tab in {tab_location}: 'arrangement' must be one of columns, rows, grid.""")
            panes = tab.get("panes")
            if not isinstance(panes, list) or len(panes) == 0:
                raise ValueError(f"""Invalid tab in {tab_location}: 'panes' must be a non-empty list.""")
            pane_names: set[str] = set()
            for pane_index, pane in enumerate(panes):
                pane_location = f"""{tab_location}.panes[{pane_index}]"""
                if not isinstance(pane, dict):
                    raise ValueError(f"""Invalid pane in {pane_location}: expected a mapping.""")
                for field in ("paneName", "startDir", "command"):
                    field_value = pane.get(field)
                    if not isinstance(field_value, str):
                        raise ValueError(f"""Invalid pane in {pane_location}: '{field}' must be a string, got {field_value!r}.""")
                pane_name = cast(str, pane["paneName"])
                if pane_name in pane_names:
                    raise ValueError(f"""Invalid pane in {pane_location}: duplicate paneName {pane_name!r} in the tab.""")
                pane_names.add(pane_name)
    return cast(LayoutsFile, document)


def write_layouts_file(path: Path, layouts_file: LayoutsFile) -> None:
    _require_layout_suffix(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""# yaml-language-server: $schema={LAYOUT_SCHEMA_URL}

{layout_yaml_text(document=layouts_file)}""",
        encoding="utf-8",
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


def serialize_layouts_to_file(layouts: list[LayoutConfig], version: Literal["0.1"], path: Path, *, write_mode: LayoutFileWriteMode) -> None:
    _get_unique_layout_indexes_by_name(layouts=layouts, source="new layouts")
    match write_mode:
        case "replace_file":
            layouts_to_write = layouts
        case "merge_by_layout_name":
            layouts_to_write = (
                _merge_layouts_by_name(existing_layouts=read_layouts_file(path=path)["layouts"], new_layouts=layouts)
                if path.exists()
                else layouts
            )
    write_layouts_file(path=path, layouts_file={"version": version, "layouts": layouts_to_write})
