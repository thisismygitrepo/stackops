import os
import platform
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from stackops.scripts.python.helpers.helpers_ai_account.models import FileAgentSupport, ManagedLoginAgentSupport, RuntimeContext
from stackops.scripts.python.helpers.helpers_ai_account.profiles import (
    copy_private_credential,
    expand_path,
    find_refresh_profile,
    list_profile_directories,
    profile_credential,
    profile_root,
    select_named_profile,
)
from stackops.scripts.python.helpers.helpers_ai_account.registry import SUPPORTED_AGENT_HELP, resolve_agent_support


app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


def _runtime_context() -> RuntimeContext:
    home_directory = Path.home()
    system_name = platform.system()
    return RuntimeContext(home=home_directory, environment=os.environ, system=system_name)


def _choose_profile(profile_directories: list[Path], support: FileAgentSupport) -> Path | None:
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    profiles_by_name = {path.name: path for path in profile_directories}
    previews = {
        path.name: (
            f"Profile: {path.name}\n"
            f"Agent: {support.display_name}\n"
            f"Source directory: {path}\n"
            f"Source file: {profile_credential(profile_directory=path, support=support)}"
        )
        for path in profile_directories
    }
    choice = choose_from_dict_with_preview(previews, extension="txt", multi=False, preview_size_percent=45)
    if choice is None:
        return None
    return profiles_by_name[choice]


@app.command()
def main(
    client: Annotated[str, typer.Argument(help=f"Agent profile source. Supported agents: {SUPPORTED_AGENT_HELP}.")],
    destination: Annotated[
        Path | None,
        typer.Option("--destination", "-d", help="Override the agent-specific active credential file."),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-p",
            help="Select a profile without the picker; with --refresh, select the backup target explicitly.",
        ),
    ] = None,
    refresh: Annotated[
        bool,
        typer.Option(
            "--refresh",
            "-r",
            help="Copy the active credential into a backup profile; omit --profile only when safe identity matching is available.",
        ),
    ] = False,
) -> None:
    try:
        agent_support = resolve_agent_support(selector=client)
    except ValueError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=2) from error

    match agent_support:
        case ManagedLoginAgentSupport():
            console.print(f"[red]{agent_support.display_name} is not file-profile-backed.[/red]")
            console.print(agent_support.reason)
            console.print(f"[yellow]{agent_support.guidance}[/yellow]")
            raise typer.Exit(code=1)
        case FileAgentSupport():
            support = agent_support

    context = _runtime_context()
    source_root = expand_path(profile_root(support=support, context=context))
    try:
        resolved_active_credential = support.resolve_active_credential(context)
        active_credential = expand_path(resolved_active_credential if destination is None else destination)
        profile_directories = list_profile_directories(source_root=source_root)
    except (OSError, ValueError) as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error

    if len(profile_directories) == 0:
        console.print(f"[red]No profile directories found under {source_root}[/red]")
        raise typer.Exit(code=1)

    if refresh:
        if not active_credential.is_file():
            console.print(f"[red]Active credential file does not exist: {active_credential}[/red]")
            raise typer.Exit(code=1)

        try:
            selected_directory = (
                select_named_profile(profile_directories=profile_directories, profile_name=profile)
                if profile is not None
                else find_refresh_profile(
                    support=support,
                    profile_directories=profile_directories,
                    active_credential=active_credential,
                )
            )
            backup_credential = profile_credential(profile_directory=selected_directory, support=support)
            copy_private_credential(source=active_credential, destination=backup_credential)
        except (OSError, ValueError) as error:
            console.print(f"[red]Failed to refresh backup: {error}[/red]")
            raise typer.Exit(code=1) from error

        console.print(f"[green]Refreshed {support.display_name} auth backup:[/green] {selected_directory.name}")
        console.print(f"[green]Wrote:[/green] {backup_credential}")
        if support.warning is not None:
            console.print(f"[yellow]{support.warning}[/yellow]")
        return

    if profile is None:
        selected_directory = _choose_profile(profile_directories=profile_directories, support=support)
        if selected_directory is None:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=130)
    else:
        try:
            selected_directory = select_named_profile(profile_directories=profile_directories, profile_name=profile)
        except ValueError as error:
            console.print(f"[red]{error}[/red]")
            raise typer.Exit(code=1) from error

    source_credential = profile_credential(profile_directory=selected_directory, support=support)
    try:
        copy_private_credential(source=source_credential, destination=active_credential)
    except OSError as error:
        console.print(f"[red]Failed to copy credential: {error}[/red]")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Installed {support.display_name} auth from profile:[/green] {selected_directory.name}")
    console.print(f"[green]Wrote:[/green] {active_credential}")
    if support.warning is not None:
        console.print(f"[yellow]{support.warning}[/yellow]")


if __name__ == "__main__":
    app()
