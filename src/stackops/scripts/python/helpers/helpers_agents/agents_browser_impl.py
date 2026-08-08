from collections.abc import Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import subprocess
from typing import assert_never

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    AGENT_BROWSER_INSTALLER_NAME,
    AGENT_BROWSER_SKILL_REPO,
    BROWSER_MCP_ROOT,
    BROWSER_SKILLS_CLI_AGENT_BY_STACKOPS_AGENT,
    BROWSER_TECH_ROOT,
    BROWSING_ROOT,
    BrowserName,
    BrowserTechName,
    DETACHED_BROWSER_LAUNCH_ID_ENV,
    PINCHTAB_INSTALLER_NAME,
    PINCHTAB_SKILL_NAME,
    PINCHTAB_SKILL_REPO,
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
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_identity import browser_launch_id
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_models import (
    BrowserLaunchDetails,
    BrowserLaunchResult,
    build_detached_launch_result,
    build_tmux_launch_result,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_launch_runtime import (
    assert_tcp_port_available as _assert_tcp_port_available,
    build_relay_command as _build_relay_command,
    find_available_localhost_port as _find_available_localhost_port,
    start_browser_process as _start_browser_process,
    start_endpoint_relay as _start_endpoint_relay,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_tmux import launch_browser_tmux
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import SKILLS_CLI_PACKAGE, SKILL_INSTALL_COMMAND_BACKEND
from stackops.scripts.python.helpers.helpers_agents.browser_launchers.registry import get_browser_launcher
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


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


def _resolve_browser_skills_cli_agent(*, agent: AGENTS) -> str:
    resolved_agent = BROWSER_SKILLS_CLI_AGENT_BY_STACKOPS_AGENT.get(agent)
    if resolved_agent is None:
        raise ValueError(f"The upstream skills CLI does not support the StackOps agent '{agent}'")
    return resolved_agent


def install_agent_browser_skill(*, agent: AGENTS, backend: SKILL_INSTALL_COMMAND_BACKEND) -> BrowserSkillInstallResult:
    skills_cli_agent = _resolve_browser_skills_cli_agent(agent=agent)
    install_root = BROWSING_ROOT.expanduser()
    install_root.mkdir(parents=True, exist_ok=True)

    from stackops.utils.installer_utils.installer_cli import main_installer_cli

    main_installer_cli(
        which=AGENT_BROWSER_INSTALLER_NAME,
        group=False,
        interactive=False,
        explore=False,
        update=True,
        version=None,
        ctx=None,
    )
    command = (backend, SKILLS_CLI_PACKAGE, "add", AGENT_BROWSER_SKILL_REPO, "--agent", skills_cli_agent, "--yes")
    _run_required_command(command=command, cwd=install_root)
    return BrowserSkillInstallResult(install_root=install_root, command=command)


def install_pinchtab_skill(*, agent: AGENTS, backend: SKILL_INSTALL_COMMAND_BACKEND) -> BrowserSkillInstallResult:
    skills_cli_agent = _resolve_browser_skills_cli_agent(agent=agent)
    install_root = BROWSER_TECH_ROOT.expanduser().joinpath(PINCHTAB_INSTALLER_NAME)
    install_root.mkdir(parents=True, exist_ok=True)

    from stackops.utils.installer_utils.installer_cli import main_installer_cli

    main_installer_cli(
        which=PINCHTAB_INSTALLER_NAME,
        group=False,
        interactive=False,
        explore=False,
        update=True,
        version=None,
        ctx=None,
    )
    command = (
        backend,
        SKILLS_CLI_PACKAGE,
        "add",
        PINCHTAB_SKILL_REPO,
        "--skill",
        PINCHTAB_SKILL_NAME,
        "--agent",
        skills_cli_agent,
        "--yes",
    )
    _run_required_command(command=command, cwd=install_root)
    return BrowserSkillInstallResult(install_root=install_root, command=command)


def install_playwright_cli(*, agent: AGENTS) -> tuple[Path, tuple[tuple[str, ...], ...]]:
    install_root = BROWSER_TECH_ROOT.expanduser().joinpath("playwright-cli")
    install_root.mkdir(parents=True, exist_ok=True)
    install_command = ("bun", "install", "-g", PLAYWRIGHT_CLI_PACKAGE_NAME)
    skills_target = "claude" if agent == "claude" else "agents"
    skills_command = (PLAYWRIGHT_CLI_COMMAND_NAME, "install", "--skills", skills_target)
    _run_required_command(command=install_command, cwd=install_root)
    _run_required_command(command=skills_command, cwd=install_root)
    return install_root, (install_command, skills_command)


def install_browser_tech(*, which: BrowserTechName, agent: AGENTS, backend: SKILL_INSTALL_COMMAND_BACKEND) -> BrowserTechInstallResult:
    match which:
        case "agent-browser":
            result = install_agent_browser_skill(agent=agent, backend=backend)
            guide_paths = write_browser_tech_files(which=which, install_root=result.install_root)
            return BrowserTechInstallResult(
                which=which,
                install_root=result.install_root,
                commands=(result.command,),
                guide_paths=guide_paths,
                mcp_servers=(),
            )
        case "pinchtab":
            result = install_pinchtab_skill(agent=agent, backend=backend)
            guide_paths = write_browser_tech_files(which=which, install_root=result.install_root)
            return BrowserTechInstallResult(
                which=which,
                install_root=result.install_root,
                commands=(result.command,),
                guide_paths=guide_paths,
                mcp_servers=(),
            )
        case "playwright-cli":
            install_root, commands = install_playwright_cli(agent=agent)
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


def launch_browser(*, browser: BrowserName, port: int, profile_name: str | None, lan: bool, detached: bool) -> BrowserLaunchResult:
    validate_port(port=port)
    launcher = get_browser_launcher(browser=browser)
    profile_path = resolve_profile_path(browser=browser, profile_name=profile_name, port=port)
    host = REMOTE_DEBUGGING_LAN if lan else REMOTE_DEBUGGING_LOCALHOST
    browser_port = _resolve_browser_endpoint_port(exposed_port=port, lan=lan)
    browser_path = resolve_browser_executable(browser=browser)
    if profile_path is not None:
        profile_path.mkdir(parents=True, exist_ok=True)
    command = build_browser_launch_command(browser=browser, browser_path=browser_path, port=browser_port, profile_path=profile_path)
    prompt_path = write_browser_prompt(
        browsing_root=BROWSING_ROOT,
        browser=browser,
        port=port,
        browser_port=browser_port,
        host=host,
        lan=lan,
        profile_path=profile_path,
    )
    details = BrowserLaunchDetails(
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
    )
    relay_command = _build_relay_command(listen_port=port, target_port=browser_port) if lan else None
    if detached:
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_processes import process_created_at
        from stackops.scripts.python.helpers.helpers_agents.agents_browser_detached_status import (
            prepare_detached_browser_registry,
            record_detached_browser_launch,
        )

        prepare_detached_browser_registry()
        launch_id = browser_launch_id(browser=browser, profile_path=profile_path, port=port)
        process_environment = dict(os.environ)
        process_environment[DETACHED_BROWSER_LAUNCH_ID_ENV] = launch_id
        process = _start_browser_process(
            command=command,
            system_name=platform.system(),
            process_label=launcher.process_label,
            environment=process_environment,
        )
        browser_process_created_at = process_created_at(process_id=process.pid, process_label=launcher.process_label)
        result = build_detached_launch_result(details=details, process_id=process.pid, relay_process_id=None)
        record_detached_browser_launch(
            result=result,
            process_created_at=browser_process_created_at,
            relay_expected=lan,
            relay_process_created_at=None,
        )
        if not lan:
            return result
        try:
            relay_process = _start_endpoint_relay(listen_port=port, target_port=browser_port, system_name=platform.system())
            relay_process_created_at = process_created_at(process_id=relay_process.pid, process_label="browser endpoint LAN relay")
        except RuntimeError as error:
            raise RuntimeError(f"Browser process {process.pid} is running, but its LAN relay failed: {error}") from error
        result = build_detached_launch_result(details=details, process_id=process.pid, relay_process_id=relay_process.pid)
        record_detached_browser_launch(
            result=result,
            process_created_at=browser_process_created_at,
            relay_expected=True,
            relay_process_created_at=relay_process_created_at,
        )
        return result
    tmux_launch = launch_browser_tmux(
        browser=browser,
        profile_path=profile_path,
        port=port,
        browser_port=browser_port,
        host=host,
        lan=lan,
        browser_command=command,
        relay_command=relay_command,
        prompt_path=prompt_path,
    )
    return build_tmux_launch_result(details=details, tmux=tmux_launch)


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
