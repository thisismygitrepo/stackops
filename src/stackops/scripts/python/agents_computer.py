from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_computer_constants import DEFAULT_COMPUTER_CONTROL_PORT


def control(
    port: Annotated[
        int, typer.Option("--port", "-p", help="Localhost port for the MCP endpoint: streamable HTTP at /mcp, SSE at /sse.")
    ] = DEFAULT_COMPUTER_CONTROL_PORT,
    headless: Annotated[
        bool,
        typer.Option("--headless", "-H", help="Restrict agent-desktop to semantic accessibility actions; omit to allow physical mouse and keyboard input."),
    ] = False,
) -> None:
    """Serve agent-desktop desktop control as a localhost MCP endpoint until interrupted."""
    import shutil
    import subprocess

    from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import tcp_port_is_open
    from stackops.scripts.python.helpers.helpers_agents.agents_computer_constants import (
        AGENT_DESKTOP_COMMAND_NAME,
        AGENT_DESKTOP_INSTALL_HINT,
        COMPUTER_CONTROL_HOST,
    )

    agent_desktop_path = shutil.which(AGENT_DESKTOP_COMMAND_NAME)
    if agent_desktop_path is None:
        typer.echo(f"""{AGENT_DESKTOP_COMMAND_NAME} is not on PATH; install it with: {AGENT_DESKTOP_INSTALL_HINT}""", err=True)
        raise typer.Exit(code=1)
    if tcp_port_is_open(host=COMPUTER_CONTROL_HOST, port=port):
        raise typer.BadParameter(f"""Port {port} is already in use; inspect it with: stackops agents computer status --port {port}""")

    command = [
        "uvx", "mcp-proxy", "--pass-environment", "--host", COMPUTER_CONTROL_HOST, "--port", str(port),
        "--", agent_desktop_path, "mcp", *(() if headless else ("--headed",)),
    ]
    typer.echo(f"""MCP endpoint: http://{COMPUTER_CONTROL_HOST}:{port}/mcp (SSE: http://{COMPUTER_CONTROL_HOST}:{port}/sse)""")
    typer.echo(f"""Input mode: {"headless semantic" if headless else "headed physical"}; stop with Ctrl+C""")
    try:
        result = subprocess.run(command, check=False)
    except KeyboardInterrupt:
        raise typer.Exit(code=130) from None
    except OSError as error:
        typer.echo(f"""Could not start {command[0]}: {error}""", err=True)
        raise typer.Exit(code=1) from error
    if result.returncode:
        raise typer.Exit(code=result.returncode if result.returncode > 0 else 128 - result.returncode)


def status(
    port: Annotated[int, typer.Option("--port", "-p", help="Localhost port of the control MCP endpoint.")] = DEFAULT_COMPUTER_CONTROL_PORT,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print endpoint and agent-desktop status as JSON.")] = False,
) -> None:
    """Show the control endpoint state and agent-desktop permissions."""
    from stackops.scripts.python.helpers.helpers_agents.agents_computer_status import (
        ComputerStatus,
        collect_agent_desktop_status,
        collect_control_endpoint_status,
        show_computer_status,
    )

    try:
        computer_status = ComputerStatus(endpoint=collect_control_endpoint_status(port=port), agent_desktop=collect_agent_desktop_status())
    except RuntimeError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error

    if json_output:
        from stackops.scripts.python.helpers.helpers_agents.agents_json import emit_agent_json

        emit_agent_json(computer_status)
        return
    show_computer_status(status=computer_status, port=port)


def get_app() -> typer.Typer:
    computer_app = typer.Typer(
        help="🖥️ <u> Desktop control for agent CLIs through MCP", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    computer_app.command(name="control", no_args_is_help=False, short_help="🎮 <c> Serve agent-desktop as a localhost MCP endpoint")(control)
    computer_app.command(name="c", no_args_is_help=False, hidden=True)(control)
    computer_app.command(name="status", no_args_is_help=False, short_help="📊 <s> Show control endpoint and agent-desktop permissions")(status)
    computer_app.command(name="s", no_args_is_help=False, hidden=True)(status)
    return computer_app
