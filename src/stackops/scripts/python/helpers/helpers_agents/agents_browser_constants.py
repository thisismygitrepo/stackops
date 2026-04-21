from pathlib import Path
from tempfile import gettempdir
from typing import Final, Literal, TypeAlias

BrowserName: TypeAlias = Literal["chrome", "brave"]

DEFAULT_BROWSER_PORT: Final[int] = 9331
AGENT_BROWSER_INSTALLER_NAME: Final[str] = "agent-browser"
AGENT_BROWSER_SKILL_REPO: Final[str] = "vercel-labs/agent-browser"
BROWSING_ROOT: Final[Path] = Path.home().joinpath("code", "agents", "browser", "vercel")
BROWSER_PROFILES_ROOT: Final[Path] = Path.home().joinpath("data", "browsers-profiles")
TEMP_BROWSER_PROFILES_ROOT: Final[Path] = Path(gettempdir()).joinpath("stackops-browser-profiles")
REMOTE_DEBUGGING_LOCALHOST: Final[str] = "127.0.0.1"
REMOTE_DEBUGGING_LAN: Final[str] = "0.0.0.0"
