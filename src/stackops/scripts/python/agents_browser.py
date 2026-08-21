from typing import Annotated, cast, get_args

import typer
from rich.console import Console

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    BROWSER_TECH_NAMES,
    BrowserName,
    BrowserTechName,
    BrowserTechSelection,
    DEFAULT_BROWSER_PORT,
    DEFAULT_BROWSER_PROFILE_PORT_START,
    ProfileBrowserName,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import TmuxBrowserLaunchResult
from stackops.scripts.python.helpers.helpers_agents.agents_browser_rich_output import build_browser_launch_summary, build_browser_launches_summary
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import SKILL_INSTALL_COMMAND_BACKEND
from stackops.utils.network.address import InterfaceIPv4Address, select_lan_interface_ipv4
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS, DEFAULT_AGENT


def install_tech(
    which: Annotated[
        BrowserTechSelection,
        typer.Option(
            "--which",
            "-w",
            help=("Browser automation tech: agent-browser, browser-use, pinchtab, playwright-cli, chrome-devtools-mcp, playwright-mcp, or all."),
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
            "--backend", "-b", help="Upstream skills CLI runner used by agent-browser and pinchtab.", case_sensitive=False, show_choices=True
        ),
    ] = "npx",
) -> None:
    """Install browser automation CLI or MCP support for agents."""
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import install_browser_tech

    try:
        resolved_agent = agent
        if resolved_agent is None:
            from stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive.common import choose_required_option, order_current_first

            agent_options = cast(tuple[AGENTS, ...], get_args(AGENTS))
            resolved_agent = cast(
                AGENTS,
                choose_required_option(options=order_current_first(options=agent_options, current=DEFAULT_AGENT), msg="Choose agent", header="Agent"),
            )
        selected_technologies: tuple[BrowserTechName, ...] = BROWSER_TECH_NAMES if which == "all" else (which,)
        results = tuple(
            install_browser_tech(which=selected_technology, agent=resolved_agent, backend=backend) for selected_technology in selected_technologies
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
            typer.echo(f"Install into an agent with: stackops agents add-mcp {','.join(result.mcp_servers)} --agent {resolved_agent} --scope local")


def launch_browser(
    port: Annotated[int, typer.Option("--port", "-p", help="Browser automation endpoint port.")] = DEFAULT_BROWSER_PORT,
    browser: Annotated[
        BrowserName, typer.Option("--browser", "-b", help="Browser to launch for agent automation.", case_sensitive=False, show_choices=True)
    ] = "chrome",
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile", "-r", help="StackOps profile under ~/data/browsers-profiles/<browser>/<profile>. Omit for a fresh port-scoped profile."
        ),
    ] = None,
    tmp: Annotated[bool, typer.Option("--tmp", "-t", help="Copy --profile to <profile>/.tmp/<random-alias> and launch the copy.")] = False,
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
        result = launch_browser_impl(browser=browser, port=port, profile_name=profile, temporary=tmp, lan=lan, detached=detached)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    Console().print(build_browser_launch_summary(result=result, lan_address=lan_address))
    if isinstance(result, TmuxBrowserLaunchResult):
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import attach_or_switch_tmux_window

        try:
            attach_or_switch_tmux_window(session_name=result.tmux.session_name, window_name=result.tmux.browser_window_name)
        except RuntimeError as error:
            typer.echo(f"Browser endpoint is running, but automatic tmux attachment failed: {error}", err=True)


def batch_launch(
    browser: Annotated[
        ProfileBrowserName,
        typer.Option("--browser", "-b", help="Browser whose saved profiles should all be launched.", case_sensitive=False, show_choices=True),
    ] = "chrome",
    port_start: Annotated[
        int, typer.Option("--port-start", "--port", "-p", help="Base port for profile endpoints; p1 uses this value plus 1.")
    ] = DEFAULT_BROWSER_PROFILE_PORT_START,
    max_profiles: Annotated[
        int | None, typer.Option("--max-profiles", "--max", "-n", min=1, help="Maximum profiles to launch; fewer are used when fewer are available.")
    ] = None,
    lan: Annotated[bool, typer.Option("--lan", "-l", help="Expose endpoints on 0.0.0.0 through localhost relays.")] = False,
    detached: Annotated[bool, typer.Option("--detached", "-d", help="Launch as background processes instead of tmux windows.")] = False,
) -> None:
    """Launch every saved profile for one browser on its assigned port."""
    lan_address: InterfaceIPv4Address | None = None
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_batch import build_browser_profile_launch_specs
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch import launch_browser as launch_browser_impl

        specs = build_browser_profile_launch_specs(browser=browser, port_start=port_start)
        if max_profiles is not None:
            specs = specs[:max_profiles]
        if lan:
            lan_address = select_lan_interface_ipv4(prefer_vpn=False)
            if lan_address is None:
                raise RuntimeError("Could not determine a local LAN IPv4 address for the browser endpoints.")
        results = tuple(
            launch_browser_impl(browser=spec.browser, port=spec.port, profile_name=spec.profile_name, temporary=False, lan=lan, detached=detached)
            for spec in specs
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    Console().print(build_browser_launches_summary(results=results, lan_address=lan_address))
    first_tmux_result = next((result for result in results if isinstance(result, TmuxBrowserLaunchResult)), None)
    if first_tmux_result is not None:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import attach_or_switch_tmux_window

        try:
            attach_or_switch_tmux_window(session_name=first_tmux_result.tmux.session_name, window_name=first_tmux_result.tmux.browser_window_name)
        except RuntimeError as error:
            typer.echo(f"Browser endpoints are running, but automatic tmux attachment failed: {error}", err=True)


def batch_close(
    browser: Annotated[
        ProfileBrowserName,
        typer.Option(
            "--browser", "-b", help="Browser whose StackOps-tracked saved-profile launches should be closed.", case_sensitive=False, show_choices=True
        ),
    ] = "chrome",
) -> None:
    """Close tracked saved-profile launches for one browser."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_batch import close_browser_profile_launches

        result = close_browser_profile_launches(browser=browser)
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    browser_label = browser.title()
    if result.closed_count == 0:
        typer.echo(f"No active {browser_label} saved-profile launches found.")
        return
    typer.echo(
        f"Closed {result.closed_count} {browser_label} saved-profile launch(es) "
        f"({len(result.tmux_launch_ids)} tmux, {len(result.detached_launch_ids)} detached)."
    )


def status(
    detached: Annotated[
        bool, typer.Option("--detached", "-d", help="Show browser processes launched with --detached instead of tmux windows.")
    ] = False,
) -> None:
    """Show active StackOps browser launches."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_status import show_detached_browser_status, show_tmux_browser_status

        if detached:
            show_detached_browser_status()
        else:
            show_tmux_browser_status()
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def declutter(
    profile: Annotated[str, typer.Option("--profile", "-r", help="StackOps profile under ~/data/browsers-profiles/<browser>/<profile>.")],
    browser: Annotated[
        ProfileBrowserName,
        typer.Option("--browser", "-b", help="Browser whose profile should be decluttered.", case_sensitive=False, show_choices=True),
    ] = "chrome",
) -> None:
    """Remove rebuildable models and caches from a closed browser profile."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles import declutter_browser_profile

        result = declutter_browser_profile(browser=browser, profile_name=profile)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Decluttered {browser} profile: {result.profile_path}")
    typer.echo(f"Removed paths: {len(result.removed_paths)}")
    typer.echo(f"Recovered: {_format_mebibytes(byte_count=result.recovered_bytes)} MiB")
    typer.echo(f"Profile size: {_format_mebibytes(byte_count=result.size_after_bytes)} MiB")


def replicate(
    count: Annotated[int, typer.Argument(min=1, help="Number of copies to create as p1, p2, ... pN.")],
    browser: Annotated[
        ProfileBrowserName,
        typer.Option("--browser", "-b", help="Browser whose base profile should be replicated.", case_sensitive=False, show_choices=True),
    ] = "chrome",
    profile: Annotated[
        str, typer.Option("--profile", "-r", help="Source StackOps profile under ~/data/browsers-profiles/<browser>/<profile>.")
    ] = "base",
) -> None:
    """Copy a closed base profile to p1 through pN without overwriting."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_profiles import replicate_browser_profile

        result = replicate_browser_profile(browser=browser, profile_name=profile, count=count)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Replicated {browser} profile: {result.source_path}")
    for destination_path in result.destination_paths:
        typer.echo(f"Created: {destination_path}")
    typer.echo(f"Source size: {_format_mebibytes(byte_count=result.source_size_bytes)} MiB")


def _format_mebibytes(*, byte_count: int) -> str:
    return f"{byte_count / (1024 * 1024):,.1f}"


def get_app() -> typer.Typer:
    browser_app = typer.Typer(
        help="🌐 <b> Browser automation for agent CLIs and MCP", no_args_is_help=True, add_help_option=True, add_completion=False
    )
    browser_app.command(name="install-tech", no_args_is_help=False, short_help="<i> Install browser CLIs, skills, or MCP configs")(install_tech)
    browser_app.command(name="i", no_args_is_help=False, hidden=True)(install_tech)
    browser_app.command(name="launch-browser", no_args_is_help=False, short_help="<l> Launch browser automation endpoint")(launch_browser)
    browser_app.command(name="l", no_args_is_help=False, hidden=True)(launch_browser)
    browser_app.command(name="batch-launch", no_args_is_help=False, short_help="<L> Launch every saved profile for one browser")(batch_launch)
    browser_app.command(name="L", no_args_is_help=False, hidden=True)(batch_launch)
    browser_app.command(name="batch-close", no_args_is_help=False, short_help="<C> Close tracked saved-profile browser launches")(batch_close)
    browser_app.command(name="C", no_args_is_help=False, hidden=True)(batch_close)
    browser_app.command(name="status", no_args_is_help=False, short_help="<s> Show active browser launches")(status)
    browser_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    browser_app.command(name="declutter", no_args_is_help=False, short_help="<d> Remove rebuildable browser profile data")(declutter)
    browser_app.command(name="d", no_args_is_help=False, hidden=True)(declutter)
    browser_app.command(name="replicate", no_args_is_help=False, short_help="<r> Copy a base profile to p1 through pN")(replicate)
    browser_app.command(name="r", no_args_is_help=False, hidden=True)(replicate)
    return browser_app
