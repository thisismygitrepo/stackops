from copy import deepcopy
import json

import typer

from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import LayoutEntry
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def choose_tabs_from_source(
    layouts_selected: list[LayoutEntry],
    choose_tabs: str | None,
    preserve_layout_groups: bool,
) -> list[LayoutConfig]:
    if choose_tabs is None:
        return deepcopy([entry.layout for entry in layouts_selected])

    flat_tab_refs: list[tuple[int, int, TabConfig]] = [
        (layout_index, tab_index, tab)
        for layout_index, entry in enumerate(layouts_selected)
        for tab_index, tab in enumerate(entry.layout["layoutTabs"])
    ]
    selected_tab_refs: set[tuple[int, int]] = set()
    if choose_tabs == "":
        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

        options_to_preview_mapping: dict[str, str] = {}
        key_to_ref: dict[str, tuple[int, int]] = {}
        for layout_index, tab_index, tab in flat_tab_refs:
            entry = layouts_selected[layout_index]
            option_key = f"""{entry.selector}::{tab['tabName']}[{tab_index}]"""
            options_to_preview_mapping[option_key] = json.dumps(
                {
                    "source_file": str(entry.source_path) if entry.source_path is not None else None,
                    "layoutName": entry.layout["layoutName"],
                    "tabIndex": tab_index,
                    "tab": tab,
                },
                indent=4,
            )
            key_to_ref[option_key] = (layout_index, tab_index)
        chosen_keys = choose_from_dict_with_preview(
            options_to_preview_mapping=options_to_preview_mapping,
            extension="json",
            multi=True,
            preview_size_percent=40,
        )
        if not chosen_keys:
            raise typer.Abort()
        selected_tab_refs = {key_to_ref[key] for key in chosen_keys}
    else:
        tab_tokens = [token.strip() for token in choose_tabs.split(",") if token.strip()]
        for token in tab_tokens:
            if "::" in token:
                layout_token, tab_token = token.split("::", 1)
                matching_layout_indexes = [
                    index
                    for index, entry in enumerate(layouts_selected)
                    if entry.selector == layout_token
                ]
                if not matching_layout_indexes:
                    matching_layout_indexes = [
                        index
                        for index, entry in enumerate(layouts_selected)
                        if entry.layout["layoutName"] == layout_token
                    ]
                if len(matching_layout_indexes) > 1:
                    alternatives = ", ".join(
                        f"""{layouts_selected[index].selector}::{tab_token}"""
                        for index in matching_layout_indexes
                    )
                    raise ValueError(f"""Tab selector '{token}' is ambiguous. Use one of: {alternatives}""")
                token_matches = {
                    (layout_index, tab_index)
                    for layout_index, tab_index, tab in flat_tab_refs
                    if layout_index in matching_layout_indexes and tab["tabName"] == tab_token
                }
            else:
                token_matches = {
                    (layout_index, tab_index)
                    for layout_index, tab_index, tab in flat_tab_refs
                    if tab["tabName"] == token
                }
            if not token_matches:
                raise ValueError(f"""Tab selector '{token}' matched no tabs.""")
            selected_tab_refs.update(token_matches)

    if not selected_tab_refs:
        raise ValueError("No tabs were selected in the chosen layouts.")
    if preserve_layout_groups:
        layouts_filtered: list[LayoutConfig] = []
        for layout_index, entry in enumerate(layouts_selected):
            tabs = [
                tab
                for tab_index, tab in enumerate(entry.layout["layoutTabs"])
                if (layout_index, tab_index) in selected_tab_refs
            ]
            if tabs:
                layouts_filtered.append({"layoutName": entry.layout["layoutName"], "layoutTabs": tabs})
        return deepcopy(layouts_filtered)

    merged_tabs = [
        tab
        for layout_index, tab_index, tab in flat_tab_refs
        if (layout_index, tab_index) in selected_tab_refs
    ]
    custom_layout: LayoutConfig = {"layoutName": "custom-tabs", "layoutTabs": merged_tabs}
    return deepcopy([custom_layout])
