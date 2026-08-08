from pathlib import Path
from tempfile import gettempdir
from typing import Final, Literal, TypeAlias

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS

BrowserName: TypeAlias = Literal["chrome", "brave", "edge", "firefox", "safari"]
BrowserTechName: TypeAlias = Literal["agent-browser", "pinchtab", "playwright-cli", "chrome-devtools-mcp", "playwright-mcp"]
BrowserTechSelection: TypeAlias = Literal["agent-browser", "pinchtab", "playwright-cli", "chrome-devtools-mcp", "playwright-mcp", "all"]

BROWSER_TECH_NAMES: Final[tuple[BrowserTechName, ...]] = (
    "agent-browser",
    "pinchtab",
    "playwright-cli",
    "chrome-devtools-mcp",
    "playwright-mcp",
)

DEFAULT_BROWSER_PORT: Final[int] = 9331
BROWSER_CDP_REQUEST_TIMEOUT_SECONDS: Final[float] = 2.0
BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS: Final[float] = 10.0
BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS: Final[float] = 0.1
BROWSER_PROCESS_TERMINATION_TIMEOUT_SECONDS: Final[float] = 5.0
BROWSER_RELAY_STARTUP_GRACE_SECONDS: Final[float] = 10.0
BROWSER_RELAY_TARGET_UNAVAILABLE_GRACE_SECONDS: Final[float] = 3.0
BROWSER_RELAY_TARGET_PROBE_INTERVAL_SECONDS: Final[float] = 0.5
BROWSER_RELAY_TARGET_PROBE_TIMEOUT_SECONDS: Final[float] = 1.0
AGENT_BROWSER_INSTALLER_NAME: Final[str] = "agent-browser"
AGENT_BROWSER_SKILL_REPO: Final[str] = "vercel-labs/agent-browser"
PINCHTAB_INSTALLER_NAME: Final[str] = "pinchtab"
PINCHTAB_SKILL_NAME: Final[str] = "pinchtab"
PINCHTAB_SKILL_REPO: Final[str] = "pinchtab/pinchtab"
PLAYWRIGHT_CLI_COMMAND_NAME: Final[str] = "playwright-cli"
PLAYWRIGHT_CLI_PACKAGE_NAME: Final[str] = "@playwright/cli"
BROWSER_TECH_ROOT: Final[Path] = Path.home().joinpath("code", "agents", "browser")
BROWSER_LAUNCH_LOCK_PATH: Final[Path] = BROWSER_TECH_ROOT.joinpath("launch.lock")
BROWSING_ROOT: Final[Path] = Path.home().joinpath("code", "agents", "browser", "vercel")
BROWSER_MCP_ROOT: Final[Path] = BROWSER_TECH_ROOT.joinpath("mcp")
BROWSER_DETACHED_LAUNCHES_ROOT: Final[Path] = BROWSER_TECH_ROOT.joinpath("detached-launches")
BROWSER_PROFILES_ROOT: Final[Path] = Path.home().joinpath("data", "browsers-profiles")
TEMP_BROWSER_PROFILES_ROOT: Final[Path] = Path(gettempdir()).joinpath("stackops-browser-profiles")
REMOTE_DEBUGGING_LOCALHOST: Final[str] = "127.0.0.1"
REMOTE_DEBUGGING_LAN: Final[str] = "0.0.0.0"
BROWSER_SKILLS_CLI_AGENT_BY_STACKOPS_AGENT: Final[dict[AGENTS, str]] = {
    "agy": "antigravity-cli",
    "cursor-agent": "cursor",
    "claude": "claude-code",
    "qwen": "qwen-code",
    "copilot": "github-copilot",
    "codex": "codex",
    "forge": "forgecode",
    "crush": "crush",
    "opencode": "opencode",
    "kilocode": "kilo",
    "cline": "cline",
    "auggie": "augment",
    "oz": "warp",
    "droid": "droid",
    "pi": "pi",
}
