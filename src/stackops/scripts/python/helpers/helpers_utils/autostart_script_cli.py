from pathlib import Path
from typing import Annotated, Literal, TypeAlias

import typer

LocalScriptSource: TypeAlias = Literal["all", "a", "workspace", "w", "user", "u", "library", "l"]
StartupKindOption: TypeAlias = Literal["script", "layout"]


def add_autostart_script(
    ctx: typer.Context,
    name: Annotated[
        str,
        typer.Argument(
            help="A script's name or file path, as `devops scripts run` takes it: a .py (run by uv), a .sh on macOS and Linux, or a .ps1 on Windows. With --kind layout, the name of a layout in your layout.yaml."
        ),
    ],
    kind: Annotated[StartupKindOption, typer.Option("--kind", "-k", help="What NAME is: one of your scripts, or one of the terminal layouts in the layout.yaml of your dotfiles.")] = "script",
    source: Annotated[LocalScriptSource, typer.Option("--source", "-s", help="Source to search for the script. Layouts are always the ones of your dotfiles.")] = "all",
    when: Annotated[
        Literal["login", "boot"],
        typer.Option("--when", "-w", help="login: when you sign in. boot: when the computer starts, before anyone signs in, which can be set up on Linux only."),
    ] = "login",
    other_systems: Annotated[
        str | None,
        typer.Option("--os", "-o", help="Other systems to list it for in startup.yaml as well, comma-separated from linux,darwin,windows. This system is always listed. For a layout, or a script in your dotfiles."),
    ] = None,
) -> None:
    import os
    import shlex

    from stackops.profile.dotfiles_constants import ALL_OS_VALUES
    from stackops.scripts.python.helpers.helpers_devops.script_resolution import resolve_script
    from stackops.scripts.python.helpers.helpers_utils.autostart_entry import StartupEntryFailure
    from stackops.scripts.python.helpers.helpers_utils.autostart_remembered import add_and_remember
    from stackops.utils.source_of_truth import DOTFILES_STARTUP_YAML_PATH, SCRIPTS_ROOT_PRIVATE

    asked = [token.strip().lower() for token in (other_systems or "").split(",") if token.strip()]
    unknown = [token for token in asked if token not in ALL_OS_VALUES]
    if unknown:
        raise typer.BadParameter(f"""{", ".join(unknown)}: not one of {", ".join(ALL_OS_VALUES)}.""", param_hint="--os")
    target = str(resolve_script(ctx=ctx, name=name, source=source, interactive=False, allow_dynamic=False)) if kind == "script" else name
    title = Path(target).name if kind == "script" else f"""Layout {name}"""
    try:
        result = add_and_remember(kind=kind, target=target, search_path=os.environ["PATH"], when=when, other_systems=tuple(system for system in ALL_OS_VALUES if system in asked))
    except ValueError as error:
        typer.echo(f"""Not added to startup: {error}""", err=True)
        raise typer.Exit(1) from error
    match result:
        case StartupEntryFailure():
            typer.echo(f"""Not added to startup: {result.message}""", err=True)
            raise typer.Exit(1)
        case _:
            moment = "when this computer starts, from the next start on" if when == "boot" else "when you sign in, from the next sign-in on"
            typer.echo(f"""✅ {title} starts {moment}.""")
            typer.echo(f"""   Entry: {result.added.entry_file}""")
            typer.echo(f"""   Runs:  {shlex.join(result.added.command)}""")
            if when == "boot":
                typer.echo("""   Your account's services start with the computer, so whatever else your account starts at sign-in does too.""")
            if result.remembered_for:
                typer.echo(f"""   Listed for {", ".join(result.remembered_for)} in {DOTFILES_STARTUP_YAML_PATH}. On another machine, `utils machine autostart-apply` starts it there.""")
            else:
                typer.echo(f"""   On this machine only: it is not in {SCRIPTS_ROOT_PRIVATE}, so startup.yaml does not list it.""")


def remove_autostart_script(
    name: Annotated[str, typer.Argument(help="The script as it was added, by its name or file path, or with --kind layout the layout's name. The script or layout itself is kept.")],
    kind: Annotated[StartupKindOption, typer.Option("--kind", "-k", help="What NAME is: a script, or a layout.")] = "script",
) -> None:
    import platform

    from stackops.scripts.python.helpers.helpers_utils.autostart_entry import StartupEntryFailure
    from stackops.scripts.python.helpers.helpers_utils.autostart_remembered import remembered_name_of, remove_and_forget

    try:
        result = remove_and_forget(kind=kind, name=name)
    except ValueError as error:
        typer.echo(f"""Not removed from startup: {error}""", err=True)
        raise typer.Exit(1) from error
    match result:
        case StartupEntryFailure():
            typer.echo(f"""Not removed from startup: {result.message}""", err=True)
            raise typer.Exit(1)
        case _:
            typer.echo(f"""✅ {Path(name).name if kind == "script" else f"Layout {name}"} no longer starts on its own here. Removed {result.entry_file}""")
            if remembered_name_of(kind=kind, target=result.target) is not None:
                typer.echo(f"""   startup.yaml no longer lists it for {platform.system().lower()}.""")


def apply_autostart_file(
    prune: Annotated[
        bool,
        typer.Option("--prune", "-p", help="Also stop the layouts and the scripts of your dotfiles that start here without being listed in startup.yaml. Scripts kept elsewhere are left alone."),
    ] = False,
) -> None:
    import os

    from stackops.scripts.python.helpers.helpers_utils.autostart_apply import apply_startup_file
    from stackops.utils.source_of_truth import DOTFILES_STARTUP_YAML_PATH

    if not DOTFILES_STARTUP_YAML_PATH.is_file():
        typer.echo(f"""Nothing to apply: there is no startup list at {DOTFILES_STARTUP_YAML_PATH} yet. `utils machine autostart-add` writes it.""")
        return
    try:
        result = apply_startup_file(search_path=os.environ["PATH"], prune=prune)
    except ValueError as error:
        typer.echo(f"""Startup list not applied: {error}""", err=True)
        raise typer.Exit(1) from error
    for added in result.added:
        typer.echo(f"""✅ {added} starts on its own here, from the next sign-in or start on.""")
    for removed in result.removed:
        typer.echo(f"""✅ {removed} no longer starts on its own here: startup.yaml does not list it.""")
    for unlisted in result.unlisted:
        typer.echo(f"""• {unlisted} starts here without being listed in startup.yaml. Pass --prune to stop it here.""")
    for failure in result.failures:
        typer.echo(f"""❌ {failure.message}""", err=True)
    if not (result.added or result.removed or result.unlisted or result.failures):
        typer.echo("This machine already starts what startup.yaml lists for it.")
    if result.failures:
        raise typer.Exit(1)
