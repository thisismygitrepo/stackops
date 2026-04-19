"""Shared layout source resolution for sessions run-style commands."""



from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

import typer

from stackops.scripts.python.helpers.helpers_sessions.sessions_impl import (
    find_layout_file,
    select_layout,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_test_layouts import (
    build_test_layouts,
    count_tabs_in_layouts,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


@dataclass(frozen=True, slots=True)
class LayoutSource:
    source_label: str
    all_layouts: list[LayoutConfig]
    is_test_layout: bool


def _clone_layouts(layouts: list[LayoutConfig]) -> list[LayoutConfig]:
    return deepcopy(layouts)


def _resolve_layouts_file_path(ctx: typer.Context, layouts_file: str | None) -> Path:
    if layouts_file is not None:
        layouts_file_resolved = Path(find_layout_file(layout_path=layouts_file))
    else:
        layouts_file_resolved = Path.home().joinpath("dotfiles/stackops/layouts.json")
    if layouts_file_resolved.exists():
        return layouts_file_resolved
    typer.echo(ctx.get_help())
    typer.echo(f"❌ Layouts file not found: {layouts_file_resolved}", err=True)
    raise typer.Exit(code=1)


def resolve_layout_source(
    ctx: typer.Context,
    layouts_file: str | None,
    test_layout: bool,
) -> LayoutSource:
    if test_layout:
        if layouts_file is not None:
            raise ValueError("--test-layout cannot be used together with --layouts-file.")
        layouts = build_test_layouts(base_dir=Path.cwd())
        typer.echo(
            f"Using generated test layout with {len(layouts)} layouts and "
            f"{count_tabs_in_layouts(layouts)} tabs."
        )
        return LayoutSource(
            source_label="generated test layout",
            all_layouts=layouts,
            is_test_layout=True,
        )
    layouts_file_resolved = _resolve_layouts_file_path(ctx=ctx, layouts_file=layouts_file)
    layouts = select_layout(
        layouts_json_file=str(layouts_file_resolved),
        selected_layouts_names=[],
        select_interactively=False,
    )
    return LayoutSource(
        source_label=str(layouts_file_resolved),
        all_layouts=layouts,
        is_test_layout=False,
    )


def load_all_layouts_from_source(layout_source: LayoutSource) -> list[LayoutConfig]:
    return _clone_layouts(layouts=layout_source.all_layouts)


def _choose_layout_names_interactively(layouts: list[LayoutConfig]) -> list[str]:
    from stackops.utils.options_utils.tv_options import (
        choose_from_dict_with_preview,
    )

    return choose_from_dict_with_preview(
        {
            layout["layoutName"]: json.dumps(layout, indent=4)
            for layout in layouts
        },
        extension="json",
        multi=True,
        preview_size_percent=40,
    )


def _select_layouts_by_names(
    layouts: list[LayoutConfig],
    selected_layout_names: list[str],
) -> list[LayoutConfig]:
    layouts_chosen: list[LayoutConfig] = []
    for selected_name in selected_layout_names:
        layout_chosen = next(
            (
                layout
                for layout in layouts
                if layout["layoutName"] == selected_name
            ),
            None,
        )
        if layout_chosen is None:
            layout_chosen = next(
                (
                    layout
                    for layout in layouts
                    if layout["layoutName"].lower() == selected_name.lower()
                ),
                None,
            )
        if layout_chosen is None:
            available_layouts = [layout["layoutName"] for layout in layouts]
            raise ValueError(
                f"Layout '{selected_name}' not found. Available layouts: {available_layouts}"
            )
        layouts_chosen.append(layout_chosen)
    return _clone_layouts(layouts=layouts_chosen)


def load_selected_layouts_from_source(
    layout_source: LayoutSource,
    choose_layouts: str | None,
) -> list[LayoutConfig]:
    if choose_layouts is None:
        return load_all_layouts_from_source(layout_source=layout_source)
    if choose_layouts == "":
        selected_layout_names = _choose_layout_names_interactively(
            layouts=layout_source.all_layouts
        )
    else:
        selected_layout_names = [
            token.strip()
            for token in choose_layouts.split(",")
            if token.strip()
        ]
    if len(selected_layout_names) == 0:
        return load_all_layouts_from_source(layout_source=layout_source)
    return _select_layouts_by_names(
        layouts=layout_source.all_layouts,
        selected_layout_names=selected_layout_names,
    )


def choose_tabs_from_source(
    layout_source: LayoutSource,
    layouts_selected: list[LayoutConfig],
    choose_tabs: str | None,
) -> list[LayoutConfig]:
    if choose_tabs is None:
        return layouts_selected
    allowed_layout_names = {layout["layoutName"] for layout in layouts_selected}
    flat_tab_refs: list[tuple[str, int, TabConfig]] = []
    for layout in layout_source.all_layouts:
        for tab_index, tab in enumerate(layout["layoutTabs"]):
            flat_tab_refs.append((layout["layoutName"], tab_index, tab))

    selected_tab_refs: set[tuple[str, int]] = set()
    if choose_tabs == "":
        from stackops.utils.options_utils.tv_options import (
            choose_from_dict_with_preview,
        )

        options_to_preview_mapping: dict[str, str] = {}
        key_to_ref: dict[str, tuple[str, int]] = {}
        for layout_name, tab_index, tab in flat_tab_refs:
            option_key = (
                f"{layout_name}::{tab['tabName']}"
                f"[{tab_index}]"
            )
            options_to_preview_mapping[option_key] = json.dumps(
                {"layoutName": layout_name, "tabIndex": tab_index, "tab": tab},
                indent=4,
            )
            key_to_ref[option_key] = (layout_name, tab_index)
        chosen_keys = choose_from_dict_with_preview(
            options_to_preview_mapping=options_to_preview_mapping,
            extension="json",
            multi=True,
            preview_size_percent=40,
        )
        selected_tab_refs = {key_to_ref[key] for key in chosen_keys}
    else:
        tab_tokens = [
            token.strip()
            for token in choose_tabs.split(",")
            if token.strip()
        ]
        for token in tab_tokens:
            if "::" in token:
                layout_name_token, tab_name_token = token.split("::", 1)
                token_matches = {
                    (layout_name, tab_index)
                    for layout_name, tab_index, tab in flat_tab_refs
                    if layout_name == layout_name_token and tab["tabName"] == tab_name_token
                }
            else:
                token_matches = {
                    (layout_name, tab_index)
                    for layout_name, tab_index, tab in flat_tab_refs
                    if tab["tabName"] == token
                }
            if len(token_matches) == 0:
                raise ValueError(f"Tab selector '{token}' matched no tabs.")
            selected_tab_refs.update(token_matches)

    merged_tabs = [
        tab
        for layout_name, tab_index, tab in flat_tab_refs
        if layout_name in allowed_layout_names
        and (layout_name, tab_index) in selected_tab_refs
    ]
    if len(merged_tabs) == 0:
        raise ValueError("No tabs were selected in the chosen layouts.")
    custom_layout: LayoutConfig = {
        "layoutName": "custom-tabs",
        "layoutTabs": merged_tabs,
    }
    return [custom_layout]
