from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import platform
import subprocess
from typing import assert_never

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import (
    AGENT_BROWSER_INSTALLER_NAME,
    AGENT_BROWSER_SKILL_REPO,
    BROWSER_MCP_ROOT,
    BROWSING_ROOT,
    BrowserName,
    BrowserTechName,
    REMOTE_DEBUGGING_LAN,
    REMOTE_DEBUGGING_LOCALHOST,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_guides import (
    get_browser_tech_mcp_servers,
    write_browser_tech_files,
)
from stackops.scripts.python.helpers.helpers_agents.agents_browser_resolution import (
    build_browser_launch_command,
    resolve_browser_executable,
    resolve_profile_path,
    validate_port,
)


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
    host: str
    port: int
    profile_path: Path
    prompt_path: Path
    process_id: int


def install_agent_browser_skill() -> BrowserSkillInstallResult:
    install_root = BROWSING_ROOT.expanduser()
    install_root.mkdir(parents=True, exist_ok=True)

    from stackops.utils.installer_utils.installer_cli import main_installer_cli

    main_installer_cli(which=AGENT_BROWSER_INSTALLER_NAME, group=False, interactive=False, update=True, version=None)
    command = ("bunx", "skills", "add", AGENT_BROWSER_SKILL_REPO)
    _run_required_command(command=command, cwd=install_root)
    return BrowserSkillInstallResult(install_root=install_root, command=command)


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
    host = REMOTE_DEBUGGING_LAN if lan else REMOTE_DEBUGGING_LOCALHOST
    browser_path = resolve_browser_executable(browser=browser)
    profile_path = resolve_profile_path(browser=browser, profile_name=profile_name, port=port)
    profile_path.mkdir(parents=True, exist_ok=True)
    command = build_browser_launch_command(browser_path=browser_path, port=port, host=host, profile_path=profile_path)
    process = _start_browser_process(command=command, system_name=platform.system())
    prompt_path = _write_prompt_file(browser=browser, port=port, host=host, profile_path=profile_path)
    return BrowserLaunchResult(
        browser=browser,
        browser_path=browser_path,
        command=command,
        host=host,
        port=port,
        profile_path=profile_path,
        prompt_path=prompt_path,
        process_id=process.pid,
    )


def _start_browser_process(*, command: Sequence[str], system_name: str) -> subprocess.Popen[bytes]:
    try:
        if system_name == "Windows":
            return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    except OSError as error:
        raise RuntimeError(f"""Failed to launch browser: {error}""") from error


def _run_required_command(*, command: Sequence[str], cwd: Path) -> None:
    try:
        completed_process = subprocess.run(command, cwd=cwd, check=False)
    except OSError as error:
        raise RuntimeError(f"""Failed to execute {' '.join(command)}: {error}""") from error
    if completed_process.returncode != 0:
        raise RuntimeError(f"""Command failed with exit code {completed_process.returncode}: {' '.join(command)}""")


def _write_prompt_file(*, browser: BrowserName, port: int, host: str, profile_path: Path) -> Path:
    prompt_path = BROWSING_ROOT.expanduser().joinpath("prompt.md")
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        f"""I launched {browser} with Chrome DevTools Protocol enabled on {host}:{port}.

When working on this machine, connect agent-browser to this existing browser session with `--cdp {port}`.
If this was launched with `--lan`, connect from another machine through this machine's LAN IP and port {port}.

Browser profile directory: {profile_path}

## Browser Automation

Use `agent-browser` for web automation. Run `agent-browser --help` for all commands.

Core workflow:

1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs like @e1 and @e2
3. `agent-browser click @e1` or `agent-browser fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes
""",
        encoding="utf-8",
    )
    return prompt_path
