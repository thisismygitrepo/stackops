from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserName, DEFAULT_BROWSER_PORT


def install_skill() -> None:
    """Install agent-browser and add the Vercel agent-browser skill."""
    try:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_impl import install_agent_browser_skill

        result = install_agent_browser_skill()
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Installed agent-browser skill in: {result.install_root}")
    typer.echo(f"Ran: {' '.join(result.command)}")


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
    browser_app.command(name="install-skill", no_args_is_help=False, short_help="<s> Install the agent-browser skill")(install_skill)
    browser_app.command(name="s", no_args_is_help=False, hidden=True)(install_skill)
    browser_app.command(name="launch-browser", no_args_is_help=False, short_help="<i> Launch Chrome or Brave for CDP automation")(launch_browser)
    browser_app.command(name="i", no_args_is_help=False, hidden=True)(launch_browser)
    return browser_app
