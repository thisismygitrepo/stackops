from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName, BrowserTechName, DEFAULT_BROWSER_PORT


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
) -> None:
    """Launch browser automation endpoint with an isolated profile when supported."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import launch_browser as launch_browser_impl

        result = launch_browser_impl(browser=browser, port=port, profile_name=profile, lan=lan)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Launched {result.process_label}: pid={result.process_id}")
    typer.echo(f"Executable: {result.browser_path}")
    typer.echo(f"{result.endpoint_short_label}: {result.host}:{result.port}")
    if result.relay_process_id is not None:
        typer.echo(f"Relay: pid={result.relay_process_id} target=127.0.0.1:{result.browser_port}")
    if result.profile_path is not None:
        typer.echo(f"Profile: {result.profile_path}")
    typer.echo(f"Prompt: {result.prompt_path}")
    if lan:
        typer.echo(f"{result.endpoint_short_label} is exposed on 0.0.0.0 through a relay; use this only on a trusted network.")


def get_app() -> typer.Typer:
    browser_app = typer.Typer(help="🌐 <b> Browser automation for agent CLIs and MCP", no_args_is_help=True, add_help_option=True, add_completion=False)
    browser_app.command(name="install-tech", no_args_is_help=False, short_help="<i> Install agent-browser, playwright-cli, or MCP configs")(install_tech)
    browser_app.command(name="i", no_args_is_help=False, hidden=True)(install_tech)
    browser_app.command(name="launch-browser", no_args_is_help=True, short_help="<l> Launch browser automation endpoint")(launch_browser)
    browser_app.command(name="l", no_args_is_help=True, hidden=True)(launch_browser)
    return browser_app
