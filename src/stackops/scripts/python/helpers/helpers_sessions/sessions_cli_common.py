"""Shared helpers for sessions run-style CLI commands."""

from pathlib import Path
import platform
from typing import Literal

import typer

from stackops.scripts.python.helpers.helpers_sessions.sessions_impl import (
    find_layout_file,
    select_layout,
)
from stackops.utils.schemas.layouts.layout_types import (
    LayoutConfig,
    TabConfig,
    substitute_home,
)

type SessionBackendOption = Literal[
    "zellij",
    "z",
    "windows-terminal",
    "wt",
    "tmux",
    "t",
    "auto",
    "a",
]
type DynamicSessionBackendOption = Literal["zellij", "z", "tmux", "t", "auto", "a"]
type ResolvedSessionBackend = Literal["zellij", "windows-terminal", "tmux"]


def resolve_layouts_file(ctx: typer.Context, layouts_file: str | None) -> Path:
    if layouts_file is not None:
        layouts_file_resolved = Path(find_layout_file(layout_path=layouts_file))
    else:
        layouts_file_resolved = Path.home().joinpath("dotfiles/stackops/layouts.json")
    if layouts_file_resolved.exists():
        return layouts_file_resolved
    typer.echo(ctx.get_help())
    typer.echo(f"❌ Layouts file not found: {layouts_file_resolved}", err=True)
    raise typer.Exit(code=1)


def load_selected_layouts(
    layouts_file_resolved: Path,
    choose_layouts: str | None,
) -> list[LayoutConfig]:
    if choose_layouts is None:
        layout_names: list[str] = []
        choose_layouts_interactively = False
    elif choose_layouts == "":
        layout_names = []
        choose_layouts_interactively = True
    else:
        layout_names = [
            name.strip()
            for name in choose_layouts.split(",")
            if name.strip()
        ]
        choose_layouts_interactively = False
    return select_layout(
        layouts_json_file=str(layouts_file_resolved),
        selected_layouts_names=layout_names,
        select_interactively=choose_layouts_interactively,
    )


def load_all_layouts(layouts_file_resolved: Path) -> list[LayoutConfig]:
    return select_layout(
        layouts_json_file=str(layouts_file_resolved),
        selected_layouts_names=[],
        select_interactively=False,
    )


def choose_tabs_from_layouts(
    layouts_file_resolved: Path,
    layouts_selected: list[LayoutConfig],
    choose_tabs: str | None,
) -> list[LayoutConfig]:
    if choose_tabs is None:
        return layouts_selected
    all_layouts = load_all_layouts(layouts_file_resolved)
    allowed_layout_names = {layout["layoutName"] for layout in layouts_selected}
    flat_tab_refs: list[tuple[str, int, TabConfig]] = []
    for layout in all_layouts:
        for tab_index, tab in enumerate(layout["layoutTabs"]):
            flat_tab_refs.append((layout["layoutName"], tab_index, tab))

    selected_tab_refs: set[tuple[str, int]] = set()
    if choose_tabs == "":
        import json

        from stackops.utils.options_utils.tv_options import (
            choose_from_dict_with_preview,
        )

        options_to_preview_mapping: dict[str, str] = {}
        key_to_ref: dict[str, tuple[str, int]] = {}
        for layout_name, tab_index, tab in flat_tab_refs:
            option_key = (
                f"{layout_name}::{tab.get('tabName', f'tab#{tab_index + 1}')}"
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
                    if layout_name == layout_name_token
                    and tab.get("tabName", "") == tab_name_token
                }
            else:
                token_matches = {
                    (layout_name, tab_index)
                    for layout_name, tab_index, tab in flat_tab_refs
                    if tab.get("tabName", "") == token
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


def substitute_home_in_layouts(
    layouts_selected: list[LayoutConfig],
) -> list[LayoutConfig]:
    layouts_modified: list[LayoutConfig] = []
    for a_layout in layouts_selected:
        layout_modified: LayoutConfig = {
            "layoutName": a_layout["layoutName"],
            "layoutTabs": substitute_home(tabs=a_layout["layoutTabs"]),
        }
        layouts_modified.append(layout_modified)
    return layouts_modified


def resolve_standard_backend(
    backend: SessionBackendOption,
) -> ResolvedSessionBackend:
    match backend:
        case "windows-terminal" | "wt":
            if platform.system().lower() != "windows":
                typer.echo(
                    "Error: Windows Terminal layouts can only be started on Windows systems.",
                    err=True,
                )
                raise typer.Exit(code=1)
            return "windows-terminal"
        case "tmux" | "t":
            if platform.system().lower() == "windows":
                typer.echo("Error: tmux is not supported on Windows.", err=True)
                raise typer.Exit(code=1)
            return "tmux"
        case "zellij" | "z":
            if platform.system().lower() == "windows":
                typer.echo("Error: Zellij is not supported on Windows.", err=True)
                raise typer.Exit(code=1)
            return "zellij"
        case "auto" | "a":
            if platform.system().lower() == "windows":
                return "windows-terminal"
            return "zellij"
        case _:
            typer.echo(f"Error: Unsupported backend '{backend}'.", err=True)
            raise typer.Exit(code=1)
