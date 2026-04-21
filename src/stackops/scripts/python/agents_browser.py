from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName, BrowserTechName, DEFAULT_BROWSER_PORT


def install_tech(
    which: Annotated[
        BrowserTechName,
        typer.Option(
            "--which",
            "-w",
            help="Browser automation technology to install or prepare.",
            case_sensitive=False,
            show_choices=True,
        ),
    ] = "agent-browser",
) -> None:
    """Install or prepare browser automation technology for agents."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import install_browser_tech

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
    port: Annotated[int, typer.Option("--port", "-p", help="Chrome DevTools Protocol remote debugging port.")] = DEFAULT_BROWSER_PORT,
    browser: Annotated[
        BrowserName,
        typer.Option("--browser", "-b", help="Browser executable to launch.", case_sensitive=False, show_choices=True),
    ] = "chrome",
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            "-r",
            help="Profile name under ~/data/browsers-profiles/<browser>/<profile>. Omit for a temp profile.",
        ),
    ] = None,
    lan: Annotated[bool, typer.Option("--lan", "-l", help="Bind CDP to 0.0.0.0 instead of localhost.")] = False,
) -> None:
    """Launch Chrome or Brave with CDP enabled for agent-browser."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import launch_browser as launch_browser_impl

        result = launch_browser_impl(browser=browser, port=port, profile_name=profile, lan=lan)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    typer.echo(f"Launched {result.browser}: pid={result.process_id}")
    typer.echo(f"Executable: {result.browser_path}")
    typer.echo(f"CDP: {result.host}:{result.port}")
    typer.echo(f"Profile: {result.profile_path}")
    typer.echo(f"Prompt: {result.prompt_path}")
    if lan:
        typer.echo("CDP is bound to 0.0.0.0; use this only on a trusted network.")


def get_app() -> typer.Typer:
    browser_app = typer.Typer(help="🌐 <b> Browser automation commands for agents", no_args_is_help=True, add_help_option=True, add_completion=False)
    browser_app.command(name="install-tech", no_args_is_help=False, short_help="<i> Install browser automation tech")(install_tech)
    browser_app.command(name="i", no_args_is_help=False, hidden=True)(install_tech)
    browser_app.command(name="launch-browser", no_args_is_help=False, short_help="<l> Launch Chrome or Brave for CDP automation")(launch_browser)
    browser_app.command(name="l", no_args_is_help=False, hidden=True)(launch_browser)
    return browser_app
