from dataclasses import dataclass
from pathlib import Path

import typer

from stackops.utils.schemas.layouts.layout_types import LayoutConfig
from stackops.utils.source_of_truth import DOTFILES_LAYOUTS_JSON_PATH


@dataclass(frozen=True, slots=True)
class LayoutEntry:
    selector: str
    layout: LayoutConfig
    source_path: Path | None


def resolve_layout_source(
    ctx: typer.Context | None,
    layouts_file: str | None,
    test_layout: bool,
) -> list[LayoutEntry]:
    if test_layout:
        if layouts_file is not None:
            raise ValueError("--test-layout cannot be used together with LAYOUTS_FILE.")
        from stackops.scripts.python.helpers.helpers_sessions.sessions_test_layouts import (
            build_test_layouts,
            count_tabs_in_layouts,
        )

        layouts = build_test_layouts(base_dir=Path.cwd())
        typer.echo(
            f"Using generated test layout with {len(layouts)} layouts and "
            f"{count_tabs_in_layouts(layouts)} tabs."
        )
        return [
            LayoutEntry(selector=layout["layoutName"], layout=layout, source_path=None)
            for layout in layouts
        ]

    source_files: list[tuple[str, Path]]
    if layouts_file is not None:
        from stackops.scripts.python.helpers.helpers_sessions.sessions_impl import find_layout_file

        source_files = [("", Path(find_layout_file(layout_path=layouts_file)))]
    else:
        source_files = [
            ("global", DOTFILES_LAYOUTS_JSON_PATH),
            ("local", Path.cwd().joinpath(".stackops", "config", "layout.json")),
        ]

    existing_files = [(source_name, path) for source_name, path in source_files if path.is_file()]
    if not existing_files:
        if ctx is not None:
            typer.echo(ctx.get_help())
        searched_paths = ", ".join(str(path) for _, path in source_files)
        typer.echo(
            f"""No layout files found: {searched_paths}

Create a layout file at one of these paths, or provide LAYOUTS_FILE explicitly.""",
            err=True,
        )
        raise typer.Exit(code=1)

    from stackops.scripts.python.helpers.helpers_sessions.sessions_impl import select_layout

    entries: list[LayoutEntry] = []
    for source_name, path in existing_files:
        layouts = select_layout(
            layouts_json_file=str(path),
            selected_layouts_names=[],
            select_interactively=False,
        )
        entries.extend(
            LayoutEntry(
                selector=f"""{source_name}:{layout["layoutName"]}""" if source_name else layout["layoutName"],
                layout=layout,
                source_path=path,
            )
            for layout in layouts
        )
    return entries


def load_selected_layouts_from_source(
    layout_source: list[LayoutEntry],
    choose_layouts: str | None,
) -> list[LayoutEntry]:
    if choose_layouts is None:
        return list(layout_source)
    if choose_layouts == "":
        import json

        from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

        selected_names = choose_from_dict_with_preview(
            options_to_preview_mapping={
                entry.selector: json.dumps(
                    {"source_file": str(entry.source_path) if entry.source_path is not None else None, **entry.layout},
                    indent=4,
                )
                for entry in layout_source
            },
            extension="json",
            multi=True,
            preview_size_percent=40,
        )
        if not selected_names:
            raise typer.Abort()
    else:
        selected_names = [token.strip() for token in choose_layouts.split(",") if token.strip()]
        if not selected_names:
            return list(layout_source)

    selected_entries: list[LayoutEntry] = []
    for selected_name in selected_names:
        matches = [entry for entry in layout_source if entry.selector == selected_name]
        if not matches:
            matches = [entry for entry in layout_source if entry.layout["layoutName"] == selected_name]
        if not matches:
            matches = [
                entry
                for entry in layout_source
                if entry.selector.lower() == selected_name.lower()
                or entry.layout["layoutName"].lower() == selected_name.lower()
            ]
        if not matches:
            available = ", ".join(entry.selector for entry in layout_source)
            raise ValueError(f"""Layout '{selected_name}' not found. Available layouts: {available}""")
        if len(matches) > 1:
            alternatives = ", ".join(entry.selector for entry in matches)
            raise ValueError(f"""Layout '{selected_name}' is ambiguous. Use one of: {alternatives}""")
        if matches[0] not in selected_entries:
            selected_entries.append(matches[0])
    return selected_entries
