from typing import Annotated, cast, get_args

import typer
from rich.console import Console

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_TECH_NAMES,
    BrowserName,
    BrowserTechName,
    BrowserTechSelection,
    DEFAULT_BROWSER_PORT,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import (
    TmuxBrowserLaunchResult,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_rich_output import build_browser_launch_summary
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import SKILL_INSTALL_COMMAND_BACKEND
from stackops.utils.network.address import InterfaceIPv4Address, select_lan_interface_ipv4
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, DEFAULT_AGENT


def install_tech(
    which: Annotated[
        BrowserTechSelection,
        typer.Option(
            "--which",
            "-w",
            help="Browser automation tech: agent-browser, pinchtab, playwright-cli, chrome-devtools-mcp, playwright-mcp, or all.",
            case_sensitive=False,
            show_choices=True,
        ),
    ] = "agent-browser",
    agent: Annotated[
        AGENTS | None,
        typer.Option(
            "--agent",
            "-a",
            help="Agent to receive the browser skill or MCP configuration guidance. Omit to choose interactively.",
            case_sensitive=False,
            show_choices=True,
        ),
    ] = None,
    backend: Annotated[
        SKILL_INSTALL_COMMAND_BACKEND,
        typer.Option(
            "--backend",
            "-b",
            help="Upstream skills CLI runner used when the selected browser tech installs a skill.",
            case_sensitive=False,
            show_choices=True,
        ),
    ] = "npx",
) -> None:
    """Install browser automation CLI or MCP support for agents."""
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import install_browser_tech

    try:
        resolved_agent = agent
        if resolved_agent is None:
            from stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.common import (
                choose_required_option,
                order_current_first,
            )

            agent_options = cast(tuple[AGENTS, ...], get_args(AGENTS))
            resolved_agent = cast(
                AGENTS,
                choose_required_option(
                    options=order_current_first(options=agent_options, current=DEFAULT_AGENT), msg="Choose agent", header="Agent"
                ),
            )
        selected_technologies: tuple[BrowserTechName, ...] = BROWSER_TECH_NAMES if which == "all" else (which,)
        results = tuple(
            install_browser_tech(which=selected_technology, agent=resolved_agent, backend=backend)
            for selected_technology in selected_technologies
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    for result in results:
        typer.echo(f"Prepared {result.which} for {resolved_agent} in: {result.install_root}")
        for command in result.commands:
            typer.echo(f"Ran: {' '.join(command)}")
        for guide_path in result.guide_paths:
            typer.echo(f"Wrote: {guide_path}")
        if len(result.mcp_servers) > 0:
            typer.echo(f"MCP catalog servers: {', '.join(result.mcp_servers)}")
            typer.echo(
                f"Install into an agent with: stackops agents add-mcp {','.join(result.mcp_servers)} --agent {resolved_agent} --scope local"
            )


def launch_browser(
    port: Annotated[int, typer.Option("--port", "-p", help="Browser automation endpoint port.")] = DEFAULT_BROWSER_PORT,
    browser: Annotated[
        BrowserName,
        typer.Option("--browser", "-b", help="Browser to launch for agent automation.", case_sensitive=False, show_choices=True),
    ] = "chrome",
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-r",
            help="StackOps profile under ~/data/browsers-profiles/<browser>/<profile>. Omit for a temp profile.",
        ),
    ] = None,
    lan: Annotated[bool, typer.Option("--lan", "-l", help="Expose endpoint on 0.0.0.0 through a localhost relay.")] = False,
    detached: Annotated[bool, typer.Option("--detached", "-d", help="Launch as background processes instead of tmux windows.")] = False,
) -> None:
    """Launch browser automation endpoint with an isolated profile when supported."""
    lan_address: InterfaceIPv4Address | None = None
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch import launch_browser as launch_browser_impl

        if lan:
            lan_address = select_lan_interface_ipv4(prefer_vpn=False)
            if lan_address is None:
                raise RuntimeError("Could not determine a local LAN IPv4 address for the browser endpoint.")
        result = launch_browser_impl(browser=browser, port=port, profile_name=profile, lan=lan, detached=detached)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    Console().print(build_browser_launch_summary(result=result, lan_address=lan_address))
    if isinstance(result, TmuxBrowserLaunchResult):
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import attach_or_switch_tmux_window

        try:
            attach_or_switch_tmux_window(
                session_name=result.tmux.session_name,
                window_name=result.tmux.browser_window_name,
            )
        except RuntimeError as error:
            typer.echo(f"Browser endpoint is running, but automatic tmux attachment failed: {error}", err=True)


def status(
    detached: Annotated[
        bool,
        typer.Option("--detached", "-d", help="Show browser processes launched with --detached instead of tmux windows."),
    ] = False,
) -> None:
    """Show active StackOps browser launches."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_status import (
            show_detached_browser_status,
            show_tmux_browser_status,
        )

        if detached:
            show_detached_browser_status()
        else:
            show_tmux_browser_status()
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def get_app() -> typer.Typer:
    browser_app = typer.Typer(help="🌐 <b> Browser automation for agent CLIs and MCP", no_args_is_help=True, add_help_option=True, add_completion=False)
    browser_app.command(name="install-tech", no_args_is_help=False, short_help="<i> Install browser CLIs, skills, or MCP configs")(install_tech)
    browser_app.command(name="i", no_args_is_help=False, hidden=True)(install_tech)
    browser_app.command(name="launch-browser", no_args_is_help=False, short_help="<l> Launch browser automation endpoint")(launch_browser)
    browser_app.command(name="l", no_args_is_help=False, hidden=True)(launch_browser)
    browser_app.command(name="status", no_args_is_help=False, short_help="<s> Show active browser launches")(status)
    browser_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    return browser_app
