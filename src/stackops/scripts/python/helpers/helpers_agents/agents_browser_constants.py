from pathlib import Path
from tempfile import gettempdir
from typing import Final, Literal, TypeAlias

from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS

BrowserName: TypeAlias = Literal["chrome", "brave", "edge", "firefox", "safari"]
ProfileBrowserName: TypeAlias = Literal["chrome", "brave", "edge", "firefox"]
ChromiumBrowserName: TypeAlias = Literal["chrome", "brave", "edge"]
BrowserSignInState: TypeAlias = Literal["signed-in", "likely", "none", "unknown"]
BrowserMultiplexer: TypeAlias = Literal["tmux", "tuios", "zellij"]
BrowserRuntime: TypeAlias = Literal["detached", "tmux", "tuios", "zellij"]
BrowserRuntimeOption: TypeAlias = Literal["detached", "d", "tmux", "t", "tuios", "u", "zellij", "z"]
BrowserTechName: TypeAlias = Literal[
    "agent-browser", "browser-use", "pinchtab", "playwright-cli", "chrome-devtools-mcp", "playwright-mcp", "omp"
]
BrowserTechSelection: TypeAlias = Literal[
    "agent-browser", "browser-use", "pinchtab", "playwright-cli", "chrome-devtools-mcp", "playwright-mcp", "omp", "all"
]
BrowserUseSkillTarget: TypeAlias = Literal["agents", "claude", "codex", "copilot", "cursor", "opencode"]

BROWSER_TECH_NAMES: Final[tuple[BrowserTechName, ...]] = (
    "agent-browser",
    "browser-use",
    "pinchtab",
    "playwright-cli",
    "chrome-devtools-mcp",
    "playwright-mcp",
    "omp",
)
BROWSER_TECH_NAMES_WITHOUT_AGENT: Final[frozenset[BrowserTechName]] = frozenset({"omp"})
BROWSER_USE_SKILL_TARGET_BY_STACKOPS_AGENT: Final[dict[AGENTS, BrowserUseSkillTarget]] = {
    "claude": "claude",
    "codex": "codex",
    "copilot": "copilot",
    "cursor-agent": "cursor",
    "opencode": "opencode",
}

DEFAULT_BROWSER_PORT: Final[int] = 9331
DEFAULT_BROWSER_PROFILE_PORT_START: Final[int] = 60000
BROWSER_CDP_REQUEST_TIMEOUT_SECONDS: Final[float] = 2.0
BROWSER_BIDI_REQUEST_TIMEOUT_SECONDS: Final[float] = 10.0
BROWSER_ENDPOINT_STARTUP_TIMEOUT_SECONDS: Final[float] = 10.0
BROWSER_ENDPOINT_PROBE_INTERVAL_SECONDS: Final[float] = 0.1
BROWSER_WINDOW_RESTORE_TIMEOUT_SECONDS: Final[float] = 5.0
BROWSER_TAB_PICKER_PREVIEW_SIZE_PERCENT: Final[float] = 40.0
BROWSER_APPLE_EVENTS_TIMEOUT_SECONDS: Final[float] = 30.0
MACOS_ACTIVATE_IGNORING_OTHER_APPS: Final[int] = 2
MACOS_AUTOMATION_DENIED_ERROR: Final[int] = -1743
BROWSER_PROCESS_TERMINATION_TIMEOUT_SECONDS: Final[float] = 5.0
BROWSER_RELAY_STARTUP_GRACE_SECONDS: Final[float] = 10.0
BROWSER_RELAY_TARGET_UNAVAILABLE_GRACE_SECONDS: Final[float] = 3.0
BROWSER_RELAY_TARGET_PROBE_INTERVAL_SECONDS: Final[float] = 0.5
BROWSER_RELAY_TARGET_PROBE_TIMEOUT_SECONDS: Final[float] = 1.0
CHROMIUM_LAUNCH_SWITCHES: Final[tuple[str, ...]] = (
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-features=CalculateNativeWinOcclusion,LockProfileCookieDatabase",
)
WINDOWS_SERVICES_SESSION_ID: Final[int] = 0
WINDOWS_DESKTOP_TASK_PREFIX: Final[str] = "stackops-browser-"
WINDOWS_DESKTOP_TASK_PRIORITY: Final[int] = 5
AGENT_BROWSER_INSTALLER_NAME: Final[str] = "agent-browser"
AGENT_BROWSER_SKILL_REPO: Final[str] = "vercel-labs/agent-browser"
BROWSER_USE_INSTALLER_NAME: Final[str] = "browser-use"
PINCHTAB_INSTALLER_NAME: Final[str] = "pinchtab"
PINCHTAB_SKILL_NAME: Final[str] = "pinchtab"
PINCHTAB_SKILL_REPO: Final[str] = "pinchtab/pinchtab"
OMP_INSTALLER_NAME: Final[BrowserTechName] = "omp"
PLAYWRIGHT_CLI_COMMAND_NAME: Final[str] = "playwright-cli"
PLAYWRIGHT_CLI_PACKAGE_NAME: Final[str] = "@playwright/cli"
BROWSER_TECH_ROOT: Final[Path] = Path.home().joinpath("code", "agents", "browser")
BROWSER_LAUNCH_LOCK_PATH: Final[Path] = BROWSER_TECH_ROOT.joinpath("launch.lock")
AGENT_BROWSER_ROOT: Final[Path] = BROWSER_TECH_ROOT.joinpath(AGENT_BROWSER_INSTALLER_NAME)
BROWSER_MCP_ROOT: Final[Path] = BROWSER_TECH_ROOT.joinpath("mcp")
BROWSER_LAUNCHES_ROOT: Final[Path] = BROWSER_TECH_ROOT.joinpath("launches")
BROWSER_MULTIPLEXER_SESSION_NAME: Final[str] = "stackops-browser"
BROWSER_TMUX_OWNER_OPTION: Final[str] = "@stackops-browser-owner"
BROWSER_TUIOS_WORKSPACE: Final[int] = 1
BROWSER_CDP_RELAY_MODULE: Final[str] = "stackops.scripts.python.helpers.helpers_agents.browser_cdp_relay"
BROWSER_RELAY_PROCESS_LABEL: Final[str] = "browser endpoint LAN relay"
BROWSER_PROFILES_ROOT: Final[Path] = Path.home().joinpath("data", "browsers-profiles")
TEMP_BROWSER_PROFILES_ROOT: Final[Path] = Path(gettempdir()).joinpath("stackops-browser-profiles")
TEMPORARY_BROWSER_PROFILE_DIRECTORY_NAME: Final[str] = ".tmp"
TEMPORARY_BROWSER_PROFILE_ALIAS_ATTEMPTS: Final[int] = 32
CHROMIUM_USER_DATA_CLEANUP_PATHS: Final[tuple[tuple[str, ...], ...]] = (
    ("OptGuideOnDeviceModel",),
    ("OptGuideOnDeviceClassifierModel",),
    ("OnDeviceHeadSuggestModel",),
    ("optimization_guide_model_store",),
    ("component_crx_cache",),
    ("extensions_crx_cache",),
    ("GPUPersistentCache",),
    ("GrShaderCache",),
    ("ShaderCache",),
)
CHROMIUM_PROFILE_CLEANUP_PATHS: Final[tuple[tuple[str, ...], ...]] = (
    ("Cache",),
    ("Code Cache",),
    ("DawnCache",),
    ("DawnGraphiteCache",),
    ("DawnWebGPUCache",),
    ("GPUCache",),
    ("GrShaderCache",),
    ("Media Cache",),
    ("ShaderCache",),
    ("AutofillAiModelCache",),
    ("image_cache",),
)
FIREFOX_PROFILE_CLEANUP_PATHS: Final[tuple[tuple[str, ...], ...]] = (("cache2",), ("shader-cache",), ("startupCache",))
CHROMIUM_ACTIVE_PORT_FILE_NAME: Final[str] = "DevToolsActivePort"
CHROMIUM_EPOCH_OFFSET_SECONDS: Final[int] = 11_644_473_600
CHROMIUM_COOKIE_DATABASE_PATHS: Final[tuple[tuple[str, ...], ...]] = (("Network", "Cookies"), ("Cookies",))
CHROMIUM_NON_USER_PROFILE_FOLDERS: Final[frozenset[str]] = frozenset({"Guest Profile", "System Profile"})
KNOWN_SERVICE_SIGN_IN_COOKIE_NAMES: Final[dict[str, frozenset[str]]] = {
    "google": frozenset({"SID", "__Secure-1PSID"}),
    "microsoft": frozenset({"ESTSAUTH", "ESTSAUTHPERSISTENT"}),
    "github": frozenset({"user_session"}),
    "slack": frozenset({"d"}),
}
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
    "cortex": "cortex",
    "deepseek": "universal",
    "crush": "crush",
    "opencode": "opencode",
    "kilocode": "kilo",
    "cline": "cline",
    "auggie": "augment",
    "oz": "warp",
    "droid": "droid",
    "pi": "pi",
    "muse": "universal",
    "maki": "codex",
    "prime-agent": "codex",
}
