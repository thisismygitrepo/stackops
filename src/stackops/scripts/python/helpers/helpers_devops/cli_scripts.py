import json
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Literal

import typer

from stackops.scripts.python.helpers.helpers_search.script_help import SCRIPT_SOURCE
from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.cli_utils.ordered_group import ordered_group


def run_script(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Script name, file path, or shell command. Following arguments are passed through.")] = "",
    source: Annotated[SCRIPT_SOURCE, typer.Option("--source", "-s", help="Source to search for the script.")] = "all",
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Choose from matching scripts interactively.")] = False,
    command: Annotated[bool, typer.Option("--command", "-c", help="Run NAME as a shell command.")] = False,
    run_in_subprocess: Annotated[
        bool, typer.Option("--subprocess", "-S", help="Run shell scripts in a child shell instead of sourcing them in the caller."),
    ] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.run_script import run_py_script

    run_py_script(
        ctx=ctx,
        name=name,
        source=source,
        interactive=interactive,
        command=command,
        run_in_subprocess=run_in_subprocess,
        forwarded_args=list(ctx.args),
    )


def list_scripts(
    source: Annotated[SCRIPT_SOURCE, typer.Option("--source", "-s", help="Source whose scripts should be listed.")] = "all",
) -> None:
    from stackops.scripts.python.helpers.helpers_search.script_help import list_available_scripts

    list_available_scripts(source=source)


def script_path(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Script to locate. Omit to print search locations as JSON.")] = "",
    source: Annotated[SCRIPT_SOURCE, typer.Option("--source", "-s", help="Source to show or search for the script.")] = "all",
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Choose from matching scripts interactively.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.script_resolution import resolve_script
    from stackops.scripts.python.helpers.helpers_devops.script_sources import get_script_locations

    if not name and not interactive:
        locations = get_script_locations(source=source)
        typer.echo(json.dumps({label: str(location) for label, location in locations.items()}, indent=2))
        return
    target = resolve_script(ctx=ctx, name=name, source=source, interactive=interactive, allow_dynamic=True)
    typer.echo(str(target))


def edit_script(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Local script name or file path to edit.")] = "",
    source: Annotated[SCRIPT_SOURCE, typer.Option("--source", "-s", help="Local source to search for the script.")] = "all",
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Choose from matching scripts interactively.")] = False,
    editor: Annotated[Literal["hx", "nano", "code"], typer.Option("--editor", "-e", help="Editor to open the script with.")] = "hx",
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.script_resolution import resolve_script

    if source in {"dynamic", "d"} and not Path(name).is_file():
        raise typer.BadParameter("Editing requires a local script source.", param_hint="--source")
    target = resolve_script(ctx=ctx, name=name, source=source, interactive=interactive, allow_dynamic=False)
    editor_bin = shutil.which(editor)
    if editor_bin is None:
        typer.echo(f"""Editor '{editor}' is not available on PATH.""", err=True)
        raise typer.Exit(code=1)
    editor_command = [editor_bin, "--wait"] if editor == "code" else [editor_bin]
    try:
        result = subprocess.run([*editor_command, str(target)], check=False)
    except OSError as error:
        typer.echo(f"""Could not edit script: {error}""", err=True)
        raise typer.Exit(code=1) from error
    if result.returncode != 0:
        typer.echo(f"""Editor exited with status code {result.returncode}.""", err=True)
        raise typer.Exit(code=result.returncode if result.returncode > 0 else 1)


def get_app() -> typer.Typer:
    app = typer.Typer(
        cls=ordered_group(("run", "list", "path", "edit")),
        help="Run, list, locate, and edit scripts. Put run options before NAME; arguments after NAME belong to the script.",
        no_args_is_help=True,
        add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    run_context: dict[str, object] = {
        "allow_extra_args": True,
        "allow_interspersed_args": False,
        "ignore_unknown_options": True,
    }
    app.command("run", no_args_is_help=True, help="🚀 <r> Run a script or shell command.", context_settings=run_context)(run_script)
    app.command("r", no_args_is_help=True, hidden=True, context_settings=run_context)(run_script)
    app.command("list", help="📋 <l> List available scripts by source.")(list_scripts)
    app.command("l", hidden=True)(list_scripts)
    app.command("path", help="📍 <p> Print script search locations or a resolved script path.")(script_path)
    app.command("p", hidden=True)(script_path)
    app.command("edit", no_args_is_help=True, help="📝 <e> Open a local script in an editor.")(edit_script)
    app.command("e", no_args_is_help=True, hidden=True)(edit_script)
    return apply_alias_markers(app)
