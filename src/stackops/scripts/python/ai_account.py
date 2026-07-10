import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from stackops.scripts.python.helpers.helpers_ai_account.models import FileAgentSupport, ManagedLoginAgentSupport, RuntimeContext
from stackops.scripts.python.helpers.helpers_ai_account.profiles import (
    backup_private_credential_automatically,
    copy_private_credential,
    expand_path,
    list_profile_directories,
    profile_credential,
    profile_root,
    select_named_profile,
)
from stackops.scripts.python.helpers.helpers_ai_account.registry import SUPPORTED_AGENT_HELP, resolve_agent_support


console = Console()


@dataclass(frozen=True, slots=True)
class AccountProfileStore:
    support: FileAgentSupport
    active_credential: Path
    profiles_root: Path


def _runtime_context() -> RuntimeContext:
    home_directory = Path.home()
    system_name = platform.system()
    return RuntimeContext(home=home_directory, environment=os.environ, system=system_name)


def _choose_retrieve_profile(profile_directories: list[Path], support: FileAgentSupport) -> Path | None:
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    profiles_by_name = {path.name: path for path in profile_directories}
    previews = {
        path.name: (
            f"Profile: {path.name}\n"
            f"Agent: {support.display_name}\n"
            f"Profile directory: {path}\n"
            f"Credential file: {profile_credential(profile_directory=path, support=support)}"
        )
        for path in profile_directories
    }
    choice = choose_from_dict_with_preview(previews, extension="txt", multi=False, preview_size_percent=45)
    if choice is None:
        return None
    return profiles_by_name[choice]


def _resolve_profile_store(agent: str, active_credential_override: Path | None) -> AccountProfileStore:
    try:
        agent_support = resolve_agent_support(selector=agent)
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
    profiles_root = expand_path(profile_root(support=support, context=context))
    try:
        resolved_active_credential = (
            support.resolve_active_credential(context)
            if active_credential_override is None
            else active_credential_override
        )
        active_credential = expand_path(resolved_active_credential)
    except (OSError, ValueError) as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error

    return AccountProfileStore(support=support, active_credential=active_credential, profiles_root=profiles_root)


def backup(
    agent: Annotated[str, typer.Argument(help=f"Agent whose active credential to back up. Supported agents: {SUPPORTED_AGENT_HELP}.")],
    profile: Annotated[
        str | None,
        typer.Option("--profile", "-p", help="Existing target profile; omit to match or create one from the active credential's safe identity."),
    ] = None,
    active_credential: Annotated[
        Path | None, typer.Option("--active-credential", "-c", help="Override the agent-specific active credential file to back up.")
    ] = None,
) -> None:
    store = _resolve_profile_store(agent=agent, active_credential_override=active_credential)
    if not store.active_credential.is_file():
        console.print(f"[red]Active credential file does not exist: {store.active_credential}[/red]")
        raise typer.Exit(code=1)

    try:
        store.profiles_root.mkdir(parents=True, exist_ok=True)
        profile_directories = list_profile_directories(source_root=store.profiles_root)
        if profile is None:
            selected_directory = backup_private_credential_automatically(
                support=store.support,
                profiles_root=store.profiles_root,
                profile_directories=profile_directories,
                active_credential=store.active_credential,
            )
        else:
            selected_directory = select_named_profile(profile_directories=profile_directories, profile_name=profile)
            selected_credential = profile_credential(profile_directory=selected_directory, support=store.support)
            copy_private_credential(source=store.active_credential, destination=selected_credential)
        backup_credential = profile_credential(profile_directory=selected_directory, support=store.support)
    except (OSError, ValueError) as error:
        console.print(f"[red]Failed to back up credential: {error}[/red]")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Backed up {store.support.display_name} credential to profile:[/green] {selected_directory.name}")
    console.print(f"[green]Wrote:[/green] {backup_credential}")
    if store.support.warning is not None:
        console.print(f"[yellow]{store.support.warning}[/yellow]")


def retrieve(
    agent: Annotated[str, typer.Argument(help=f"Agent whose saved credential to retrieve. Supported agents: {SUPPORTED_AGENT_HELP}.")],
    profile: Annotated[str | None, typer.Option("--profile", "-p", help="Source profile; omit to select one interactively.")] = None,
    active_credential: Annotated[
        Path | None, typer.Option("--active-credential", "-c", help="Override the agent-specific active credential file to replace.")
    ] = None,
) -> None:
    store = _resolve_profile_store(agent=agent, active_credential_override=active_credential)
    try:
        profile_directories = list_profile_directories(source_root=store.profiles_root)
    except (OSError, ValueError) as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error

    if len(profile_directories) == 0:
        console.print(f"[red]No profiles found under {store.profiles_root}[/red]")
        raise typer.Exit(code=1)

    if profile is None:
        selected_directory = _choose_retrieve_profile(profile_directories=profile_directories, support=store.support)
        if selected_directory is None:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=130)
    else:
        try:
            selected_directory = select_named_profile(profile_directories=profile_directories, profile_name=profile)
        except ValueError as error:
            console.print(f"[red]{error}[/red]")
            raise typer.Exit(code=1) from error

    saved_credential = profile_credential(profile_directory=selected_directory, support=store.support)
    try:
        copy_private_credential(source=saved_credential, destination=store.active_credential)
    except OSError as error:
        console.print(f"[red]Failed to retrieve credential: {error}[/red]")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Retrieved {store.support.display_name} credential from profile:[/green] {selected_directory.name}")
    console.print(f"[green]Wrote:[/green] {store.active_credential}")
    if store.support.warning is not None:
        console.print(f"[yellow]{store.support.warning}[/yellow]")


def get_app() -> typer.Typer:
    account_app = typer.Typer(
        help="Back up active AI agent credentials or retrieve saved profiles.", no_args_is_help=True, add_help_option=True, add_completion=False
    )
    account_app.command(name="backup", no_args_is_help=True, short_help="Save an active credential to a profile")(backup)
    account_app.command(name="b", no_args_is_help=True, hidden=True)(backup)
    account_app.command(name="retrieve", no_args_is_help=True, short_help="Retrieve a saved profile as the active credential")(retrieve)
    account_app.command(name="r", no_args_is_help=True, hidden=True)(retrieve)
    return account_app


app = get_app()


if __name__ == "__main__":
    app()
