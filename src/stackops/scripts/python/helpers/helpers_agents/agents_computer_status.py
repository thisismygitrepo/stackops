import json
import shutil
import subprocess
from dataclasses import dataclass
from http.client import HTTPException
from typing import Literal, TypeAlias
from urllib.request import urlopen

from rich import box
from rich.console import Console
from rich.table import Table

from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import tcp_port_is_open
from stackops.scripts.python.helpers.helpers_agents.agents_computer_constants import (
    AGENT_DESKTOP_COMMAND_NAME,
    AGENT_DESKTOP_INSTALL_HINT,
    AGENT_DESKTOP_STATUS_TIMEOUT_SECONDS,
    COMPUTER_CONTROL_HOST,
    COMPUTER_CONTROL_PROBE_TIMEOUT_SECONDS,
)
from stackops.utils.schemas.yaml_schema import JsonValue

ControlEndpointState: TypeAlias = Literal["running", "stopped", "foreign"]


@dataclass(frozen=True)
class ControlEndpointStatus:
    state: ControlEndpointState
    mcp_url: str
    sse_url: str
    last_activity: str | None
    active_sse_connections: int | None


@dataclass(frozen=True)
class AgentDesktopStatus:
    executable: str
    version: str
    platform: str
    permissions: dict[str, str]


@dataclass(frozen=True)
class ComputerStatus:
    endpoint: ControlEndpointStatus
    agent_desktop: AgentDesktopStatus | None


def collect_control_endpoint_status(*, port: int) -> ControlEndpointStatus:
    base_url = f"""http://{COMPUTER_CONTROL_HOST}:{port}"""
    mcp_url = f"""{base_url}/mcp"""
    sse_url = f"""{base_url}/sse"""
    if not tcp_port_is_open(host=COMPUTER_CONTROL_HOST, port=port):
        return ControlEndpointStatus(state="stopped", mcp_url=mcp_url, sse_url=sse_url, last_activity=None, active_sse_connections=None)
    try:
        with urlopen(f"""{base_url}/status""", timeout=COMPUTER_CONTROL_PROBE_TIMEOUT_SECONDS) as response:
            payload: JsonValue = json.loads(response.read())
    except (OSError, HTTPException, json.JSONDecodeError):
        return ControlEndpointStatus(state="foreign", mcp_url=mcp_url, sse_url=sse_url, last_activity=None, active_sse_connections=None)
    match payload:
        case {"api_last_activity": str(last_activity), "active_sse_connections": int(active_sse_connections), "server_instances": dict()}:
            return ControlEndpointStatus(
                state="running", mcp_url=mcp_url, sse_url=sse_url, last_activity=last_activity, active_sse_connections=active_sse_connections
            )
        case _:
            return ControlEndpointStatus(state="foreign", mcp_url=mcp_url, sse_url=sse_url, last_activity=None, active_sse_connections=None)


def collect_agent_desktop_status() -> AgentDesktopStatus | None:
    executable = shutil.which(AGENT_DESKTOP_COMMAND_NAME)
    if executable is None:
        return None
    try:
        completed = subprocess.run(
            [executable, "status"], capture_output=True, text=True, check=False, timeout=AGENT_DESKTOP_STATUS_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"""Could not run {executable} status: {error}""") from error
    try:
        envelope: JsonValue = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"""{executable} status did not print JSON (exit {completed.returncode}): {completed.stderr.strip()}""") from error
    unexpected_output = RuntimeError(f"""Unexpected {executable} status output: {completed.stdout.strip()}""")
    match envelope:
        case {"ok": True, "data": dict() as data}:
            pass
        case {"ok": False, "error": dict() as error_details}:
            raise RuntimeError(f"""{executable} status failed with {error_details.get("code")}: {error_details.get("message")}""")
        case _:
            raise unexpected_output
    match data:
        case {"version": str(version), "platform": str(platform), "permissions": dict() as raw_permissions}:
            pass
        case _:
            raise unexpected_output
    permission_entries: dict[str, JsonValue] = raw_permissions
    permissions: dict[str, str] = {}
    for name, entry in permission_entries.items():
        match entry:
            case {"state": str(state)}:
                permissions[name] = state
            case _:
                raise unexpected_output
    return AgentDesktopStatus(executable=executable, version=version, platform=platform, permissions=permissions)


def show_computer_status(*, status: ComputerStatus, port: int) -> None:
    table = Table(title="StackOps computer control status", box=box.SIMPLE_HEAVY, show_header=False)
    table.add_column("Item", style="bold")
    table.add_column("Value", overflow="fold")

    endpoint = status.endpoint
    match endpoint.state:
        case "running":
            table.add_row("Endpoint", f"""[green]running[/green] on port {port}""")
            table.add_row("MCP URL", endpoint.mcp_url)
            table.add_row("SSE URL", endpoint.sse_url)
            table.add_row("Last activity", "-" if endpoint.last_activity is None else endpoint.last_activity)
            table.add_row("SSE connections", "-" if endpoint.active_sse_connections is None else str(endpoint.active_sse_connections))
        case "stopped":
            table.add_row("Endpoint", f"""[yellow]stopped[/yellow]; start it with: stackops agents computer control --port {port}""")
        case "foreign":
            table.add_row("Endpoint", f"""[red]port {port} is held by a process that is not mcp-proxy[/red]""")

    agent_desktop = status.agent_desktop
    if agent_desktop is None:
        table.add_row("agent-desktop", f"""[red]not on PATH[/red]; install it with: {AGENT_DESKTOP_INSTALL_HINT}""")
    else:
        table.add_row("agent-desktop", f"""{agent_desktop.version} ({agent_desktop.platform}) at {agent_desktop.executable}""")
        for name, state in agent_desktop.permissions.items():
            table.add_row(f"""Permission: {name}""", state)
    Console().print(table)
