import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TypedDict, get_args

from stackops.scripts.python.helpers.helpers_webui.constants import VERSION_PROBE_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_constants import (
    CLOUD_MOUNT_MULTIPLEXERS,
    MULTIPLEXER_CAPABILITIES,
    MultiplexerCapability,
    MultiplexerRole,
)
from stackops.utils.default_multiplexer import BUILTIN_DEFAULT_AGENT_MULTIPLEXER, BUILTIN_DEFAULT_SESSION_MULTIPLEXER, resolve_session_multiplexer
from stackops.utils.schemas.config.config_types import StackOpsConfig
from stackops.utils.schemas.config.multiplexer_types import AGENT_MULTIPLEXERS, SESSION_MULTIPLEXERS, SessionMultiplexer
from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH, read_stackops_config

VERSION_PATTERN = re.compile(r"\d[\w.+-]*")


@dataclass(frozen=True, slots=True)
class MultiplexerProblem:
    status: int
    message: str


# One of the two defaults. `chosen` is false while the settings file names none; `name` is then `fallback`, the one built into StackOps.
class DefaultView(TypedDict):
    name: str
    chosen: bool
    fallback: str


# `problem` is why StackOps cannot use an installed multiplexer as it is, in the CLI's own words. `in_catalog` is read only while the page has
# one to install or update, and is false for all of them the rest of the time.
class MultiplexerView(TypedDict):
    name: str
    installed: bool
    version: str
    supported: bool
    problem: str
    in_catalog: bool
    roles: list[MultiplexerRole]
    works_with: list[MultiplexerCapability]


class MultiplexerOverview(TypedDict):
    session: DefaultView
    agent: DefaultView
    capabilities: list[MultiplexerCapability]
    multiplexers: list[MultiplexerView]


# The settings file as the CLI reads it, or None while there is none yet. One that fails the CLI's check stops every command that falls back on
# a default, so it is reported as it is and never read around.
def read_settings() -> StackOpsConfig | None | MultiplexerProblem:
    if not DOTFILES_STACKOPS_CONFIG_PATH.exists():
        return None
    try:
        return read_stackops_config()
    except (OSError, ValueError) as error:
        return MultiplexerProblem(status=422, message=str(error))


# Which multiplexers each further feature takes, from the lists the CLI itself checks a choice against.
def _capable_multiplexers() -> dict[MultiplexerCapability, tuple[str, ...]]:
    from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserMultiplexer
    from stackops.scripts.python.helpers.helpers_sessions.sessions_dynamic_display import DynamicSessionBackend
    from stackops.scripts.python.helpers.helpers_sessions.terminal_export import TerminalExportBackend

    return {
        "batch": get_args(DynamicSessionBackend),
        "save": get_args(TerminalExportBackend),
        "browsers": get_args(BrowserMultiplexer),
        "mounts": CLOUD_MOUNT_MULTIPLEXERS,
        "agents": AGENT_MULTIPLEXERS,
    }


# What the program says about itself. tmux is the one that takes `-V` and refuses `--version`.
def _read_version(name: SessionMultiplexer) -> str:
    try:
        answer = subprocess.run(
            [name, "-V" if name == "tmux" else "--version"],
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=VERSION_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    found = VERSION_PATTERN.search(answer.stdout.partition("\n")[0]) if answer.returncode == 0 else None
    return "" if found is None else found.group()


def _multiplexer_view(name: SessionMultiplexer, capable: dict[MultiplexerCapability, tuple[str, ...]]) -> MultiplexerView:
    installed = shutil.which(name) is not None
    try:
        resolve_session_multiplexer(multiplexer=name)
        supported = True
    except ValueError:
        supported = False
    problem = ""
    # Zellij is the one multiplexer the CLI holds to a minimum version, which it checks before every use.
    if installed and supported and name == "zellij":
        from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import require_zellij

        try:
            require_zellij()
        except ValueError as error:
            problem = str(error)
    return {
        "name": name,
        "installed": installed,
        "version": _read_version(name=name) if installed else "",
        "supported": supported,
        "problem": problem,
        "in_catalog": False,
        "roles": ["session", "agent"] if name in AGENT_MULTIPLEXERS else ["session"],
        "works_with": [capability for capability in MULTIPLEXER_CAPABILITIES if name in capable[capability]],
    }


# The apps the catalog can install on this system. A catalog that does not load offers no link here; the Apps page is where it says why.
def _catalog_names() -> frozenset[str]:
    from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError
    from stackops.utils.installer_utils.installer_runner import get_installers_from_source
    from stackops.utils.schemas.installer.installer_types import get_normalized_arch, get_os_name

    try:
        installers = get_installers_from_source(source="all", user_path=None, os=get_os_name(), arch=get_normalized_arch(), which_cats=None)
    except InstallerDataFileError:
        return frozenset()
    return frozenset(installer["appName"] for installer in installers)


# Both defaults and every multiplexer the CLI knows, with how each stands on this machine. The programs are asked for their versions side by
# side, so the answer takes as long as the slowest one. What is running in each is left to `terminal_multiplexer_sessions`, which is slower.
def read_multiplexer_overview() -> MultiplexerOverview | MultiplexerProblem:
    settings = read_settings()
    match settings:
        case MultiplexerProblem():
            return settings
        case _:
            chosen_session = None if settings is None else settings.get("default_session_multiplexer")
            chosen_agent = None if settings is None else settings.get("default_agent_multiplexer")
    capable = _capable_multiplexers()
    with ThreadPoolExecutor(max_workers=len(SESSION_MULTIPLEXERS)) as pool:
        views = list(pool.map(lambda name: _multiplexer_view(name=name, capable=capable), SESSION_MULTIPLEXERS))
    if any(view["supported"] and (not view["installed"] or view["problem"] != "") for view in views):
        catalog = _catalog_names()
        for view in views:
            view["in_catalog"] = view["name"] in catalog
    return {
        "session": {
            "name": chosen_session if chosen_session is not None else BUILTIN_DEFAULT_SESSION_MULTIPLEXER,
            "chosen": chosen_session is not None,
            "fallback": BUILTIN_DEFAULT_SESSION_MULTIPLEXER,
        },
        "agent": {
            "name": chosen_agent if chosen_agent is not None else BUILTIN_DEFAULT_AGENT_MULTIPLEXER,
            "chosen": chosen_agent is not None,
            "fallback": BUILTIN_DEFAULT_AGENT_MULTIPLEXER,
        },
        "capabilities": list(MULTIPLEXER_CAPABILITIES),
        "multiplexers": views,
    }
