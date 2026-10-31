from typing import Annotated

import typer

from stackops.utils.schemas.config.multiplexer_types import AgentMultiplexer, SessionMultiplexer

MULTIPLEXER_SETUP_HELP = "Select the default session and agent multiplexers and save them in the StackOps config."


def setup_multiplexer(
    session: Annotated[
        SessionMultiplexer | None,
        typer.Option("--session", "-s", help="Use this session multiplexer (terminal commands) instead of prompting."),
    ] = None,
    agent: Annotated[
        AgentMultiplexer | None,
        typer.Option("--agent", "-a", help="Use this agent multiplexer (agents status/parallel) instead of prompting."),
    ] = None,
) -> None:
    from rich.console import Console
    from rich.panel import Panel

    from stackops.scripts.python.helpers.helpers_devops.cli_config_setup_config import load_stackops_config_for_setup, write_stackops_config
    from stackops.scripts.python.helpers.helpers_devops.register_interactive import ask_choice
    from stackops.utils.default_multiplexer import BUILTIN_DEFAULT_AGENT_MULTIPLEXER, BUILTIN_DEFAULT_SESSION_MULTIPLEXER
    from stackops.utils.managed_files import get_managed_file_spec
    from stackops.utils.schemas.config.multiplexer_types import AGENT_MULTIPLEXERS, SESSION_MULTIPLEXERS

    existing_config = load_stackops_config_for_setup()
    configured_session = existing_config.get("default_session_multiplexer") if existing_config is not None else None
    configured_agent = existing_config.get("default_agent_multiplexer") if existing_config is not None else None
    selected_session: SessionMultiplexer = session if session is not None else ask_choice(
        "Default session multiplexer",
        help_text="terminal run, run-all, attach, kill, trace, summary and export use this one when --backend is omitted.",
        choices=SESSION_MULTIPLEXERS,
        default=configured_session if configured_session is not None else BUILTIN_DEFAULT_SESSION_MULTIPLEXER,
    )
    selected_agent: AgentMultiplexer = agent if agent is not None else ask_choice(
        "Default agent multiplexer",
        help_text="agents status and agents parallel use this one when --backend is omitted.",
        choices=AGENT_MULTIPLEXERS,
        default=configured_agent if configured_agent is not None else BUILTIN_DEFAULT_AGENT_MULTIPLEXER,
    )
    write_stackops_config(
        existing_config=existing_config,
        values={"default_session_multiplexer": selected_session, "default_agent_multiplexer": selected_agent},
    )
    Console().print(
        Panel(
            f"""Default session multiplexer is now [bold]{selected_session}[/bold].
Default agent multiplexer is now [bold]{selected_agent}[/bold].
Saved in {get_managed_file_spec("config").user_path}.""",
            title="Configuration Saved",
            border_style="green",
            padding=(1, 2),
        )
    )
