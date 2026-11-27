from copy import deepcopy

import typer

from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import LayoutEntry
from stackops.utils.schemas.layouts.layout_enabled import OFF_MARK, drop_disabled
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def choose_tabs_from_source(
    layouts_selected: list[LayoutEntry],
    choose_tabs: str | None,
    preserve_layout_groups: bool,
) -> list[LayoutConfig]:
    if choose_tabs is None:
        return drop_disabled(deepcopy([entry.layout for entry in layouts_selected]))

    flat_tab_refs: list[tuple[int, int, TabConfig]] = [
        (layout_index, tab_index, tab)
        for layout_index, entry in enumerate(layouts_selected)
        for tab_index, tab in enumerate(entry.layout["layoutTabs"])
    ]
    selected_tab_refs: set[tuple[int, int]] = set()
    if choose_tabs == "":
        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview
        from stackops.utils.schemas.yaml_document import yaml_document_text

        options_to_preview_mapping: dict[str, str] = {}
        key_to_ref: dict[str, tuple[int, int]] = {}
        for layout_index, tab_index, tab in flat_tab_refs:
            entry = layouts_selected[layout_index]
            launches_with_layout = entry.layout.get("enabled", True) and tab.get("enabled", True)
            option_key = f"""{entry.selector}::{tab['tabName']}[{tab_index}]{"" if launches_with_layout else OFF_MARK}"""
            options_to_preview_mapping[option_key] = yaml_document_text(
                document={
                    "source_file": str(entry.source_path) if entry.source_path is not None else None,
                    "layoutName": entry.layout["layoutName"],
                    "tabIndex": tab_index,
                    "tab": tab,
                },
            )
            key_to_ref[option_key] = (layout_index, tab_index)
        chosen_keys = choose_from_dict_with_preview(
            options_to_preview_mapping=options_to_preview_mapping,
            extension="yaml",
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
                named_tab_refs = [(layout_index, tab_index) for layout_index, tab_index, tab in flat_tab_refs if tab["tabName"] == token]
                token_matches = {
                    (layout_index, tab_index)
                    for layout_index, tab_index in named_tab_refs
                    if layouts_selected[layout_index].layout.get("enabled", True)
                }
                if named_tab_refs and not token_matches:
                    alternatives = ", ".join(sorted({f"""{layouts_selected[layout_index].selector}::{token}""" for layout_index, _tab_index in named_tab_refs}))
                    raise ValueError(f"""Tab '{token}' is only in layouts that are switched off. Name its layout to launch it: {alternatives}""")
            if not token_matches:
                raise ValueError(f"""Tab selector '{token}' matched no tabs.""")
            selected_tab_refs.update(token_matches)

    if not selected_tab_refs:
        raise ValueError("No tabs were selected in the chosen layouts.")
    # A tab that was named or picked launches even when it or its layout is switched off; its panes that are off stay off.
    chosen_tabs_by_layout: list[list[TabConfig]] = [
        [
            {**tab, "enabled": True}
            for tab_index, tab in enumerate(entry.layout["layoutTabs"])
            if (layout_index, tab_index) in selected_tab_refs
        ]
        for layout_index, entry in enumerate(layouts_selected)
    ]
    layouts_chosen: list[LayoutConfig]
    if preserve_layout_groups:
        layouts_chosen = [
            {"layoutName": entry.layout["layoutName"], "layoutTabs": tabs}
            for entry, tabs in zip(layouts_selected, chosen_tabs_by_layout, strict=True)
            if tabs
        ]
    else:
        layouts_chosen = [{"layoutName": "custom-tabs", "layoutTabs": [tab for tabs in chosen_tabs_by_layout for tab in tabs]}]
    return drop_disabled(deepcopy(layouts_chosen))
