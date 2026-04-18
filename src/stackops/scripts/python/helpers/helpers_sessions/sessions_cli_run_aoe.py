"""CLI implementation for sessions run-aoe command."""



from pathlib import Path
from typing import Literal

import typer

from stackops.scripts.python.helpers.helpers_sessions.sessions_aoe_impl import (
    AoeLaunchOptions,
    run_layouts_via_aoe,
)
from stackops.scripts.python.helpers.helpers_sessions.sessions_impl import (
    find_layout_file,
    select_layout,
)
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig, substitute_home


def run_aoe_cli(
    ctx: typer.Context,
    layouts_file: str | None,
    choose_layouts: str | None,
    choose_tabs: str | None,
    sleep_inbetween: float,
    max_tabs: int,
    agent: str | None,
    model: str | None,
    provider: str | None,
    sandbox: str | None,
    yolo: bool,
    cmd: str | None,
    args: list[str],
    env: list[str],
    force: bool,
    dry_run: bool,
    aoe_bin: str,
    tab_command_mode: Literal["prompt", "cmd", "ignore"],
    subsitute_home: bool,
    launch: bool,
) -> None:
    if layouts_file is not None:
        layouts_file_resolved = Path(find_layout_file(layout_path=layouts_file))
    else:
        layouts_file_resolved = Path.home().joinpath("dotfiles/stackops/layouts.json")
    if not layouts_file_resolved.exists():
        typer.echo(ctx.get_help())
        typer.echo(f"❌ Layouts file not found: {layouts_file_resolved}", err=True)
        raise typer.Exit(code=1)

    if choose_layouts is None:
        layouts_names_resolved: list[str] = []
        choose_layouts_interactively = False
    elif choose_layouts == "":
        layouts_names_resolved = []
        choose_layouts_interactively = True
    else:
        layouts_names_resolved = [name.strip() for name in choose_layouts.split(",") if name.strip()]
        choose_layouts_interactively = False

    layouts_selected: list[LayoutConfig] = select_layout(
        layouts_json_file=str(layouts_file_resolved),
        selected_layouts_names=layouts_names_resolved,
        select_interactively=choose_layouts_interactively,
    )

    if choose_tabs is not None:
        all_layouts: list[LayoutConfig] = select_layout(
            layouts_json_file=str(layouts_file_resolved),
            selected_layouts_names=[],
            select_interactively=False,
        )
        allowed_layout_names = {layout["layoutName"] for layout in layouts_selected}
        flat_tab_refs: list[tuple[str, int, TabConfig]] = []
        for layout in all_layouts:
            for tab_index, tab in enumerate(layout["layoutTabs"]):
                flat_tab_refs.append((layout["layoutName"], tab_index, tab))

        selected_tab_refs: set[tuple[str, int]] = set()
        if choose_tabs == "":
            import json
            from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

            options_to_preview_mapping: dict[str, str] = {}
            key_to_ref: dict[str, tuple[str, int]] = {}
            for layout_name, tab_index, tab in flat_tab_refs:
                option_key = f"{layout_name}::{tab.get('tabName', f'tab#{tab_index + 1}')}[{tab_index}]"
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
            tab_tokens = [token.strip() for token in choose_tabs.split(",") if token.strip()]
            for token in tab_tokens:
                if "::" in token:
                    layout_name_token, tab_name_token = token.split("::", 1)
                    token_matches = {
                        (layout_name, tab_index)
                        for layout_name, tab_index, tab in flat_tab_refs
                        if layout_name == layout_name_token and tab.get("tabName", "") == tab_name_token
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

        grouped_tabs: dict[str, list[TabConfig]] = {layout["layoutName"]: [] for layout in layouts_selected}
        for layout_name, tab_index, tab in flat_tab_refs:
            if layout_name in allowed_layout_names and (layout_name, tab_index) in selected_tab_refs:
                grouped_tabs.setdefault(layout_name, []).append(tab)

        layouts_filtered: list[LayoutConfig] = []
        for layout in layouts_selected:
            tabs = grouped_tabs.get(layout["layoutName"], [])
            if len(tabs) == 0:
                continue
            layouts_filtered.append({"layoutName": layout["layoutName"], "layoutTabs": tabs})
        if len(layouts_filtered) == 0:
            raise ValueError("No tabs were selected in the chosen layouts.")
        layouts_selected = layouts_filtered

    if subsitute_home:
        layouts_modified: list[LayoutConfig] = []
        for a_layout in layouts_selected:
            layout_modified: LayoutConfig = {
                "layoutName": a_layout["layoutName"],
                "layoutTabs": substitute_home(tabs=a_layout["layoutTabs"]),
            }
            layouts_modified.append(layout_modified)
        layouts_selected = layouts_modified

    for a_layout in layouts_selected:
        if len(a_layout["layoutTabs"]) > max_tabs:
            raise ValueError(
                f"Layout '{a_layout.get('layoutName', 'Unnamed')}' has "
                f"{len(a_layout['layoutTabs'])} tabs which exceeds the max of {max_tabs}."
            )

    options = AoeLaunchOptions(
        aoe_bin=aoe_bin,
        agent=agent,
        model=model,
        provider=provider,
        sandbox=sandbox,
        yolo=yolo,
        cmd=cmd,
        extra_agent_args=tuple(args),
        env_vars=tuple(env),
        force=force,
        dry_run=dry_run,
        sleep_inbetween=sleep_inbetween,
        tab_command_mode=tab_command_mode,
        launch=launch,
    )

    try:
        run_layouts_via_aoe(layouts_selected=layouts_selected, options=options)
    except ValueError as e:
        typer.echo(str(e))
        raise typer.Exit(1) from e
