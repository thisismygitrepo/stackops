from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS

CLOUD_SETUP_HELP = "Select an rclone remote and create or update the StackOps config and schema."
AGENT_SETUP_HELP = "Select the default coding agent and save it in the StackOps config."
SETUP_HELP = "Guided creation of StackOps user configuration files."


def _select_remote(remote_names: tuple[str, ...], configured_remote: str | None) -> str:
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_choice

    default_remote = configured_remote if configured_remote in remote_names else remote_names[0]
    return ask_choice(
        "Default rclone remote",
        help_text=(
            "StackOps stores the name of an existing rclone remote here; credentials remain in rclone's own config. "
            "The name is saved without its trailing colon."
        ),
        choices=remote_names,
        default=default_remote,
    )


def setup_cloud(
    cloud: Annotated[
        str | None,
        typer.Option("--cloud", "-c", help="Use this existing rclone remote instead of prompting."),
    ] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Write without confirmation. Requires --cloud.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import (
        exit_with_setup_error,
        load_stackops_config_for_setup,
        write_stackops_config,
    )
    from stackops.utils.cloud.rclone import list_remote_names
    from stackops.utils.managed_files import get_managed_file_spec, managed_schema_path

    if yes and cloud is None:
        exit_with_setup_error("--yes requires --cloud so the selected remote is explicit.")

    try:
        remote_names = list_remote_names()
    except RuntimeError as exc:
        exit_with_setup_error(
            f"Could not inspect rclone remotes:\n{exc}\n\n"
            "Create or repair an rclone remote with:\n"
            "  rclone config"
        )
    if len(remote_names) == 0:
        exit_with_setup_error(
            "No rclone remotes are configured. StackOps stores a remote name, not cloud credentials.\n\n"
            "Create a remote first:\n"
            "  rclone config\n\n"
            "Then rerun:\n"
            "  devops config setup cloud"
        )

    config_spec = get_managed_file_spec("config")
    config_path = config_spec.user_path
    schema_path = managed_schema_path(spec=config_spec, data_path=config_path)
    existing_config = load_stackops_config_for_setup()
    configured_remote = existing_config.get("default_rclone_config") if existing_config is not None else None
    if cloud is None:
        selected_remote = _select_remote(remote_names=remote_names, configured_remote=configured_remote)
    else:
        selected_remote = cloud.strip()
        if selected_remote == "":
            exit_with_setup_error("--cloud must name an existing rclone remote.")
        if selected_remote.endswith(":"):
            exit_with_setup_error("Pass the rclone remote name without its trailing colon.")
        if selected_remote not in remote_names:
            exit_with_setup_error(
                f"Rclone remote {selected_remote!r} does not exist. Available remotes: {', '.join(remote_names)}\n\n"
                "Create another remote with:\n"
                "  rclone config"
            )

    config_action = "Create" if existing_config is None else "Update"

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold cyan", no_wrap=True)
    summary.add_column(overflow="fold")
    summary.add_row("Action", config_action)
    summary.add_row("Rclone remote", selected_remote)
    summary.add_row("Config", config_path.as_posix())
    summary.add_row("Schema", schema_path.as_posix())
    console = Console()
    console.print(Panel(summary, title="Cloud Configuration", border_style="cyan", padding=(1, 2)))
    if not yes and not typer.confirm("Write this configuration?", default=True):
        raise typer.Exit(code=0)

    write_stackops_config(existing_config=existing_config, values={"default_rclone_config": selected_remote})
    console.print(
        Panel(
            f"Default cloud is now [bold]{selected_remote}[/bold].\n"
            "Commands that omit --cloud will use this rclone remote.",
            title="Configuration Saved",
            border_style="green",
            padding=(1, 2),
        )
    )


def setup_agent(
    agent: Annotated[
        AGENTS | None,
        typer.Option("--agent", "-a", help="Use this agent instead of prompting."),
    ] = None,
) -> None:
    from typing import get_args

    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import load_stackops_config_for_setup, write_stackops_config
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_choice
    from stackops.utils.managed_files import get_managed_file_spec

    existing_config = load_stackops_config_for_setup()
    configured_agent = existing_config.get("default_agent") if existing_config is not None else None
    agent_choices: tuple[AGENTS, ...] = get_args(AGENTS)
    selected_agent: AGENTS = agent if agent is not None else ask_choice(
        "Default agent",
        help_text="Agent commands that omit --agent use this one.",
        choices=agent_choices,
        default=configured_agent if configured_agent is not None else agent_choices[0],
    )
    write_stackops_config(existing_config=existing_config, values={"default_agent": selected_agent})
    Console().print(
        Panel(
            f"Default agent is now [bold]{selected_agent}[/bold] in {get_managed_file_spec("config").user_path}.",
            title="Configuration Saved",
            border_style="green",
            padding=(1, 2),
        )
    )


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_devops import cli_config_setup_domains as setup_domains
    from stackops.scripts.python.helpers.helpers_devops import cli_config_setup_email as setup_email

    app = typer.Typer(
        help=SETUP_HELP, no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command("cloud", no_args_is_help=False, help=f"☁️ <c> {CLOUD_SETUP_HELP}")(setup_cloud)
    app.command("c", no_args_is_help=False, help=CLOUD_SETUP_HELP, hidden=True)(setup_cloud)
    app.command("email", no_args_is_help=False, help=f"📧 <e> {setup_email.EMAIL_SETUP_HELP}")(setup_email.setup_email)
    app.command("e", no_args_is_help=False, help=setup_email.EMAIL_SETUP_HELP, hidden=True)(setup_email.setup_email)
    app.command("agent", no_args_is_help=False, help=f"🤖 <a> {AGENT_SETUP_HELP}")(setup_agent)
    app.command("a", no_args_is_help=False, help=AGENT_SETUP_HELP, hidden=True)(setup_agent)
    app.command("data", no_args_is_help=False, help=f"💾 <d> {setup_domains.DATA_SETUP_HELP}")(setup_domains.setup_data)
    app.command("d", no_args_is_help=False, help=setup_domains.DATA_SETUP_HELP, hidden=True)(setup_domains.setup_data)
    app.command("dotfiles", no_args_is_help=False, help=f"📄 <f> {setup_domains.DOTFILES_SETUP_HELP}")(setup_domains.setup_dotfiles)
    app.command("f", no_args_is_help=False, help=setup_domains.DOTFILES_SETUP_HELP, hidden=True)(setup_domains.setup_dotfiles)
    app.command("layouts", no_args_is_help=False, help=f"🧩 <l> {setup_domains.LAYOUTS_SETUP_HELP}")(setup_domains.setup_layouts)
    app.command("l", no_args_is_help=False, help=setup_domains.LAYOUTS_SETUP_HELP, hidden=True)(setup_domains.setup_layouts)
    app.command("secrets", no_args_is_help=False, help=f"🔐 <s> {setup_domains.SECRETS_SETUP_HELP}")(setup_domains.setup_secrets)
    app.command("s", no_args_is_help=False, help=setup_domains.SECRETS_SETUP_HELP, hidden=True)(setup_domains.setup_secrets)
    return app
