import json
from pathlib import Path
from typing import Annotated, Literal

import typer


def resolve_layout_file(*, layouts_file: Path | None, source: Literal["workspace", "w", "user", "u"] | None) -> Path:
    if layouts_file is not None:
        return layouts_file.expanduser().absolute()
    if source is None:
        raise typer.BadParameter("Provide --custom-path or --source workspace|user. Use terminal path to see available files.")
    match source:
        case "workspace" | "w":
            from stackops.utils.repos.stackops_paths import require_current_repo_stackops_path

            try:
                return require_current_repo_stackops_path(path_kind="layout_yaml")
            except ValueError as error:
                raise typer.BadParameter(str(error)) from error
        case "user" | "u":
            from stackops.utils.source_of_truth import DOTFILES_LAYOUT_YAML_PATH

            return DOTFILES_LAYOUT_YAML_PATH


def describe_layout_file(*, path: Path) -> str:
    from stackops.utils.schemas.layouts.layout_file import read_layouts_file

    if not path.exists():
        return "🆕 missing · will be created from the example template"
    if not path.is_file():
        return "⛔ exists but is not a file"
    try:
        layouts = read_layouts_file(path=path)["layouts"]
    except (OSError, ValueError):
        return "⚠️ exists · invalid layout file"
    tabs = [tab for layout in layouts for tab in layout["layoutTabs"]]
    panes_count = sum(len(tab["panes"]) for tab in tabs)
    lines_count = len(path.read_text(encoding="utf-8").splitlines())
    return f"""✅ exists · layouts: {len(layouts)} · tabs: {len(tabs)} · panes: {panes_count} · lines: {lines_count}"""


def path_layouts(
    layouts_file: Annotated[
        Path | None, typer.Option("--custom-path", "-p", dir_okay=False, help="Layout YAML file. Overrides --source; omit to show user and workspace paths."),
    ] = None,
    source: Annotated[
        Literal["workspace", "w", "user", "u"] | None,
        typer.Option("--source", "-s", help="Show one config file's paths. Ignored when --custom-path is provided."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    if layouts_file is not None or source is not None:
        file_path = resolve_layout_file(layouts_file=layouts_file, source=source)
        run_managed_file_action(kind="layouts", action="path", path=file_path)
        return

    from stackops.scripts.python.helpers.helpers_sessions.sessions_layout_source import default_layout_source_paths
    from stackops.utils.managed_file_operations import describe_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    spec = get_managed_file_spec("layouts")
    paths = {
        name: describe_managed_file(spec=spec, data_path=data_path)
        for name, data_path in default_layout_source_paths().items()
    }
    typer.echo(json.dumps(paths, indent=2))


def init_layouts(
    layouts_file: Annotated[
        Path | None, typer.Option("--custom-path", "-p", dir_okay=False, help="Layout YAML file to create if missing. Overrides --source."),
    ] = None,
    source: Annotated[
        Literal["workspace", "w", "user", "u"] | None,
        typer.Option("--source", "-s", help="Config file to initialize. Ignored when --custom-path is provided."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    file_path = resolve_layout_file(layouts_file=layouts_file, source=source)
    run_managed_file_action(kind="layouts", action="init", path=file_path)


def validate_layouts(
    layouts_file: Annotated[
        Path | None, typer.Option("--custom-path", "-p", dir_okay=False, help="Layout YAML file to validate. Overrides --source."),
    ] = None,
    source: Annotated[
        Literal["workspace", "w", "user", "u"] | None,
        typer.Option("--source", "-s", help="Config file to validate. Ignored when --custom-path is provided."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    file_path = resolve_layout_file(layouts_file=layouts_file, source=source)
    run_managed_file_action(kind="layouts", action="validate", path=file_path)
