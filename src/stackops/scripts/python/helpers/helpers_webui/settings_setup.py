from pathlib import Path
from typing import Literal, TypedDict, get_args

from stackops.utils.default_agent import resolve_agent
from stackops.utils.default_multiplexer import BUILTIN_DEFAULT_AGENT_MULTIPLEXER, BUILTIN_DEFAULT_SESSION_MULTIPLEXER
from stackops.utils.schemas.config.config_types import StackOpsConfigValues
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS
from stackops.utils.source_of_truth import (
    DOTFILES_LAYOUT_YAML_PATH,
    DOTFILES_ROOT,
    DOTFILES_STACKOPS_CONFIG_PATH,
    DOTFILES_USER_BACKUP_PATH,
    DOTFILES_USER_MAPPER_PATH,
    read_stackops_config,
)

type SetupList = Literal["backups", "dotfiles", "layouts", "logins"]


# One of the lists a setup step adds to. `count` is how many entries it holds, and None while the file is missing or cannot be read; `problem`
# is then why, in the words of the reader the CLI uses.
class ListState(TypedDict):
    path: str
    exists: bool
    count: int | None
    problem: str


# Where the guided setup stands. A default nobody chose is an empty text, and `*_in_use` is what a command then falls back on.
# `settings_problem` is set when the settings file is there and fails the check every StackOps command gives it; the defaults are then unknown.
# `dotfiles_folder` says whether the folder all of these live in is on this machine yet.
class SetupState(TypedDict):
    dotfiles_folder: bool
    settings_path: str
    settings_exists: bool
    settings_problem: str
    cloud: str
    email_profile: str
    email_address: str
    agent: str
    agent_in_use: str
    agents: list[str]
    session_multiplexer: str
    session_multiplexer_in_use: str
    agent_multiplexer: str
    agent_multiplexer_in_use: str
    backups: ListState
    dotfiles: ListState
    layouts: ListState
    logins: ListState


# How many entries a list holds, read with the reader the CLI uses for it. Of the secrets file only this number leaves: no name, no value.
def _count_entries(which: SetupList, path: Path) -> int:
    match which:
        case "backups":
            from stackops.scripts.python.helpers.helpers_cloud.backup_config import load_backup_config_file

            backups = load_backup_config_file(path=path, empty_as_config=True)
            return 0 if backups is None else sum(len(group) for group in backups.values())
        case "dotfiles":
            from stackops.profile.dotfiles_mapper import load_dotfiles_mapper

            return sum(len(section) for section in load_dotfiles_mapper(path=path).values())
        case "layouts":
            from stackops.utils.schemas.layouts.layout_file import read_layouts_file

            return len(read_layouts_file(path=path)["layouts"])
        case "logins":
            from stackops.secrets.loader import load_secrets_file

            return len(load_secrets_file(secrets_path=path)["entries"])


def _list_state(which: SetupList, path: Path) -> ListState:
    if not path.is_file():
        return {"path": str(path), "exists": False, "count": None, "problem": ""}
    try:
        return {"path": str(path), "exists": True, "count": _count_entries(which=which, path=path), "problem": ""}
    except (OSError, ValueError) as error:
        return {"path": str(path), "exists": True, "count": None, "problem": str(error)}


def read_setup_state() -> SetupState:
    from stackops.secrets.paths import SECRETS_DOFILE

    chosen: StackOpsConfigValues = {}
    settings_exists = DOTFILES_STACKOPS_CONFIG_PATH.exists()
    settings_problem = ""
    if settings_exists:
        try:
            chosen = read_stackops_config()
        except (OSError, ValueError) as error:
            settings_problem = str(error)
    session_multiplexer = chosen.get("default_session_multiplexer", "")
    agent_multiplexer = chosen.get("default_agent_multiplexer", "")
    return {
        "dotfiles_folder": DOTFILES_ROOT.is_dir(),
        "settings_path": str(DOTFILES_STACKOPS_CONFIG_PATH),
        "settings_exists": settings_exists,
        "settings_problem": settings_problem,
        "cloud": chosen.get("default_rclone_config", ""),
        "email_profile": chosen.get("default_email_config", ""),
        "email_address": chosen.get("default_email_address", ""),
        "agent": chosen.get("default_agent", ""),
        # The CLI's resolver reads the settings file again, so it is asked only once that file is known to be readable.
        "agent_in_use": "" if settings_problem else resolve_agent(agent=None),
        "agents": list(get_args(AGENTS)),
        "session_multiplexer": session_multiplexer,
        "session_multiplexer_in_use": session_multiplexer or BUILTIN_DEFAULT_SESSION_MULTIPLEXER,
        "agent_multiplexer": agent_multiplexer,
        "agent_multiplexer_in_use": agent_multiplexer or BUILTIN_DEFAULT_AGENT_MULTIPLEXER,
        "backups": _list_state(which="backups", path=DOTFILES_USER_BACKUP_PATH),
        "dotfiles": _list_state(which="dotfiles", path=DOTFILES_USER_MAPPER_PATH),
        "layouts": _list_state(which="layouts", path=DOTFILES_LAYOUT_YAML_PATH),
        "logins": _list_state(which="logins", path=SECRETS_DOFILE),
    }
