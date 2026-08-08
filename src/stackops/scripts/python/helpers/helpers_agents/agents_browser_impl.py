from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import assert_never

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    AGENT_BROWSER_INSTALLER_NAME,
    AGENT_BROWSER_SKILL_REPO,
    BROWSER_MCP_ROOT,
    BROWSER_SKILLS_CLI_AGENT_BY_STACKOPS_AGENT,
    BROWSER_TECH_ROOT,
    BROWSING_ROOT,
    BrowserTechName,
    PINCHTAB_INSTALLER_NAME,
    PINCHTAB_SKILL_NAME,
    PINCHTAB_SKILL_REPO,
    PLAYWRIGHT_CLI_COMMAND_NAME,
    PLAYWRIGHT_CLI_PACKAGE_NAME,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_guides import (
    get_browser_tech_mcp_servers,
    write_browser_tech_files,
)
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import SKILLS_CLI_PACKAGE, SKILL_INSTALL_COMMAND_BACKEND
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


def _run_required_command(*, command: Sequence[str], cwd: Path) -> None:
    try:
        completed_process = subprocess.run(command, cwd=cwd, check=False)
    except OSError as error:
        raise RuntimeError(f"""Failed to execute {' '.join(command)}: {error}""") from error
    if completed_process.returncode != 0:
        raise RuntimeError(f"""Command failed with exit code {completed_process.returncode}: {' '.join(command)}""")
