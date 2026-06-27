from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName, BrowserTechName, DEFAULT_BROWSER_PORT
from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import DetachedBrowserLaunchResult, TmuxBrowserLaunchResult


def install_tech(
    which: Annotated[
        BrowserTechName,
        typer.Option(
            "--which",
            "-w",
            help="Browser automation tech: agent-browser, playwright-cli, chrome-devtools-mcp, or playwright-mcp.",
            case_sensitive=False,
            show_choices=True,
        ),
    ] = "agent-browser",
) -> None:
    """Install browser automation CLI or MCP support for agents."""
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import install_browser_tech

    try:
        result = install_browser_tech(which=which)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Prepared {result.which} in: {result.install_root}")
    for command in result.commands:
        typer.echo(f"Ran: {' '.join(command)}")
    for guide_path in result.guide_paths:
        typer.echo(f"Wrote: {guide_path}")
    if len(result.mcp_servers) > 0:
        typer.echo(f"MCP catalog servers: {', '.join(result.mcp_servers)}")
        typer.echo(f"Install into an agent with: stackops agents add-mcp {','.join(result.mcp_servers)} --agent codex --scope local")


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
    detached: Annotated[bool, typer.Option("--detached", help="Launch as background processes instead of tmux windows.")] = False,
) -> None:
    """Launch browser automation endpoint with an isolated profile when supported."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import launch_browser as launch_browser_impl

        result = launch_browser_impl(browser=browser, port=port, profile_name=profile, lan=lan, detached=detached)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    match result:
        case DetachedBrowserLaunchResult():
            typer.echo(f"Launched {result.process_label}: pid={result.process_id}")
            if result.relay_process_id is not None:
                typer.echo(f"Relay: pid={result.relay_process_id} target=127.0.0.1:{result.browser_port}")
        case TmuxBrowserLaunchResult():
            typer.echo(f"Launched {result.process_label} in tmux session: {result.tmux.session_name}")
            typer.echo(f"Browser window: {result.tmux.browser_window_name}")
            if result.tmux.relay_window_name is not None:
                typer.echo(f"Relay window: {result.tmux.relay_window_name} target=127.0.0.1:{result.browser_port}")
            typer.echo(f"Attach: {' '.join(result.tmux.attach_command)}")
    typer.echo(f"Executable: {result.browser_path}")
    typer.echo(f"{result.endpoint_short_label}: {result.host}:{result.port}")
    if result.profile_path is not None:
        typer.echo(f"Profile: {result.profile_path}")
    typer.echo(f"Prompt: {result.prompt_path}")
    if lan:
        typer.echo(f"{result.endpoint_short_label} is exposed on 0.0.0.0 through a relay; use this only on a trusted network.")
    if isinstance(result, TmuxBrowserLaunchResult):
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import attach_or_switch_tmux_session

        try:
            attach_or_switch_tmux_session(session_name=result.tmux.session_name)
        except RuntimeError as error:
            typer.echo(str(error), err=True)
            raise typer.Exit(code=1) from error


def status() -> None:
    """Show active StackOps browser tmux sessions."""
    try:
        from rich import box
        from rich.console import Console
        from rich.table import Table

        from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import collect_browser_tmux_status

        rows = collect_browser_tmux_status()
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    launch_count = len({row.metadata.launch_id for row in rows})
    window_count = len({row.window_id for row in rows})
    table = Table(
        title=f"StackOps browser tmux: {launch_count} launch(es), {window_count} window(s), {len(rows)} pane(s)",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Session", style="cyan", overflow="fold")
    table.add_column("Launch", overflow="fold")
    table.add_column("Role")
    table.add_column("Browser")
    table.add_column("Profile", overflow="fold")
    table.add_column("Endpoint")
    table.add_column("Window")
    table.add_column("Pane")
    table.add_column("State")
    table.add_column("PID", justify="right")
    table.add_column("Command")
    table.add_column("Profile Path", overflow="fold")
    table.add_column("Prompt", overflow="fold")

    for row in rows:
        state = "dead" if row.pane_dead else "running"
        endpoint = f"{row.metadata.host}:{row.metadata.port}"
        if row.metadata.lan == "yes":
            endpoint = f"{endpoint} -> 127.0.0.1:{row.metadata.browser_port}"
        table.add_row(
            row.session_name,
            row.metadata.launch_id,
            row.metadata.role,
            row.metadata.browser,
            row.metadata.profile,
            endpoint,
            f"{row.window_index}:{row.window_name}",
            f"{row.pane_index} {row.pane_id}",
            state,
            row.pane_pid,
            row.pane_current_command,
            row.metadata.profile_path,
            row.metadata.prompt_path,
        )

    Console().print(table)


def get_app() -> typer.Typer:
    browser_app = typer.Typer(help="🌐 <b> Browser automation for agent CLIs and MCP", no_args_is_help=True, add_help_option=True, add_completion=False)
    browser_app.command(name="install-tech", no_args_is_help=False, short_help="<i> Install agent-browser, playwright-cli, or MCP configs")(install_tech)
    browser_app.command(name="i", no_args_is_help=False, hidden=True)(install_tech)
    browser_app.command(name="launch-browser", no_args_is_help=True, short_help="<l> Launch browser automation endpoint")(launch_browser)
    browser_app.command(name="l", no_args_is_help=True, hidden=True)(launch_browser)
    browser_app.command(name="status", no_args_is_help=False, short_help="<s> Show active browser tmux sessions")(status)
    browser_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    return browser_app
