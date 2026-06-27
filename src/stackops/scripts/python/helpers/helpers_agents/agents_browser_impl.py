from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import platform
import socket
import subprocess
import sys
from typing import assert_never

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    AGENT_BROWSER_INSTALLER_NAME,
    AGENT_BROWSER_SKILL_REPO,
    BROWSER_MCP_ROOT,
    BROWSER_TECH_ROOT,
    BROWSING_ROOT,
    BrowserName,
    BrowserTechName,
    PLAYWRIGHT_CLI_COMMAND_NAME,
    PLAYWRIGHT_CLI_PACKAGE_NAME,
    REMOTE_DEBUGGING_LAN,
    REMOTE_DEBUGGING_LOCALHOST,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_guides import (
    get_browser_tech_mcp_servers,
    write_browser_tech_files,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_prompt import write_browser_prompt
from stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution import (
    build_browser_launch_command,
    resolve_browser_executable,
    resolve_profile_path,
    validate_port,
)
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher


@dataclass(frozen=True)
class BrowserSkillInstallResult:
    install_root: Path
    command: tuple[str, ...]


@dataclass(frozen=True)
class BrowserTechInstallResult:
    which: BrowserTechName
    install_root: Path
    commands: tuple[tuple[str, ...], ...]
    guide_paths: tuple[Path, ...]
    mcp_servers: tuple[str, ...]


@dataclass(frozen=True)
class BrowserLaunchResult:
    browser: BrowserName
    browser_path: Path
    command: tuple[str, ...]
    endpoint_label: str
    endpoint_short_label: str
    process_label: str
    host: str
    port: int
    browser_port: int
    profile_path: Path | None
    prompt_path: Path
    process_id: int
    relay_process_id: int | None


def install_agent_browser_skill() -> BrowserSkillInstallResult:
    install_root = BROWSING_ROOT.expanduser()
    install_root.mkdir(parents=True, exist_ok=True)

    from stackops.utils.installer_utils.installer_cli import main_installer_cli

    main_installer_cli(which=AGENT_BROWSER_INSTALLER_NAME, group=False, interactive=False, update=True, version=None)
    command = ("bunx", "skills@latest", "add", AGENT_BROWSER_SKILL_REPO, "--yes")
    _run_required_command(command=command, cwd=install_root)
    return BrowserSkillInstallResult(install_root=install_root, command=command)


def install_playwright_cli() -> tuple[Path, tuple[tuple[str, ...], ...]]:
    install_root = BROWSER_TECH_ROOT.expanduser().joinpath("playwright-cli")
    install_root.mkdir(parents=True, exist_ok=True)
    install_command = ("bun", "install", "-g", PLAYWRIGHT_CLI_PACKAGE_NAME)
    skills_command = (PLAYWRIGHT_CLI_COMMAND_NAME, "install", "--skills")
    _run_required_command(command=install_command, cwd=install_root)
    _run_required_command(command=skills_command, cwd=install_root)
    return install_root, (install_command, skills_command)


def install_browser_tech(*, which: BrowserTechName) -> BrowserTechInstallResult:
    match which:
        case "agent-browser":
            result = install_agent_browser_skill()
            guide_paths = write_browser_tech_files(which=which, install_root=result.install_root)
            return BrowserTechInstallResult(
                which=which,
                install_root=result.install_root,
                commands=(result.command,),
                guide_paths=guide_paths,
                mcp_servers=(),
            )
        case "playwright-cli":
            install_root, commands = install_playwright_cli()
            guide_paths = write_browser_tech_files(which=which, install_root=install_root)
            return BrowserTechInstallResult(
                which=which,
                install_root=install_root,
                commands=commands,
                guide_paths=guide_paths,
                mcp_servers=(),
            )
        case "chrome-devtools-mcp" | "playwright-mcp":
            install_root = BROWSER_MCP_ROOT.expanduser().joinpath(which)
            guide_paths = write_browser_tech_files(which=which, install_root=install_root)
            return BrowserTechInstallResult(
                which=which,
                install_root=install_root,
                commands=(),
                guide_paths=guide_paths,
                mcp_servers=get_browser_tech_mcp_servers(which=which),
            )
        case _:
            assert_never(which)


def launch_browser(*, browser: BrowserName, port: int, profile_name: str | None, lan: bool) -> BrowserLaunchResult:
    validate_port(port=port)
    launcher = get_browser_launcher(browser=browser)
    profile_path = resolve_profile_path(browser=browser, profile_name=profile_name, port=port)
    host = REMOTE_DEBUGGING_LAN if lan else REMOTE_DEBUGGING_LOCALHOST
    browser_port = _resolve_browser_endpoint_port(exposed_port=port, lan=lan)
    browser_path = resolve_browser_executable(browser=browser)
    if profile_path is not None:
        profile_path.mkdir(parents=True, exist_ok=True)
    command = build_browser_launch_command(browser=browser, browser_path=browser_path, port=browser_port, profile_path=profile_path)
    process = _start_browser_process(command=command, system_name=platform.system(), process_label=launcher.process_label)
    relay_process = _start_endpoint_relay(listen_port=port, target_port=browser_port, system_name=platform.system()) if lan else None
    prompt_path = write_browser_prompt(
        browsing_root=BROWSING_ROOT,
        browser=browser,
        port=port,
        browser_port=browser_port,
        host=host,
        lan=lan,
        profile_path=profile_path,
    )
    return BrowserLaunchResult(
        browser=browser,
        browser_path=browser_path,
        command=command,
        endpoint_label=launcher.endpoint_label,
        endpoint_short_label=launcher.endpoint_short_label,
        process_label=launcher.process_label,
        host=host,
        port=port,
        browser_port=browser_port,
        profile_path=profile_path,
        prompt_path=prompt_path,
        process_id=process.pid,
        relay_process_id=None if relay_process is None else relay_process.pid,
    )


def _start_browser_process(*, command: Sequence[str], system_name: str, process_label: str) -> subprocess.Popen[bytes]:
    return _start_background_process(command=command, system_name=system_name, failure_message=f"""Failed to launch {process_label}""")


def _start_endpoint_relay(*, listen_port: int, target_port: int, system_name: str) -> subprocess.Popen[bytes]:
    command = _build_relay_command(listen_port=listen_port, target_port=target_port)
    return _start_background_process(command=command, system_name=system_name, failure_message="Failed to launch browser endpoint LAN relay")


def _start_background_process(*, command: Sequence[str], system_name: str, failure_message: str) -> subprocess.Popen[bytes]:
    try:
        if system_name == "Windows":
            return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as error:
        raise RuntimeError(f"""{failure_message}: {error}""") from error


def _run_required_command(*, command: Sequence[str], cwd: Path) -> None:
    try:
        completed_process = subprocess.run(command, cwd=cwd, check=False)
    except OSError as error:
        raise RuntimeError(f"""Failed to execute {' '.join(command)}: {error}""") from error
    if completed_process.returncode != 0:
        raise RuntimeError(f"""Command failed with exit code {completed_process.returncode}: {' '.join(command)}""")


def _resolve_browser_endpoint_port(*, exposed_port: int, lan: bool) -> int:
    if lan:
        _assert_tcp_port_available(host=REMOTE_DEBUGGING_LAN, port=exposed_port)
        return _find_available_localhost_port(excluded_port=exposed_port)
    _assert_tcp_port_available(host=REMOTE_DEBUGGING_LOCALHOST, port=exposed_port)
    return exposed_port


def _assert_tcp_port_available(*, host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
        probe_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe_socket.bind((host, port))
        except OSError as error:
            raise RuntimeError(f"""TCP port {host}:{port} is not available: {error}""") from error


def _find_available_localhost_port(*, excluded_port: int) -> int:
    for _attempt in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe_socket:
            probe_socket.bind((REMOTE_DEBUGGING_LOCALHOST, 0))
            chosen_port = int(probe_socket.getsockname()[1])
        if chosen_port != excluded_port:
            return chosen_port
    raise RuntimeError("Could not find an internal localhost browser endpoint port")


def _build_relay_command(*, listen_port: int, target_port: int) -> tuple[str, ...]:
    return (
        sys.executable,
        "-m",
        "stackops.scripts.python.helpers.helpers_agents.browser_cdp_relay",
        "--listen-host",
        REMOTE_DEBUGGING_LAN,
        "--listen-port",
        str(listen_port),
        "--target-host",
        REMOTE_DEBUGGING_LOCALHOST,
        "--target-port",
        str(target_port),
    )
