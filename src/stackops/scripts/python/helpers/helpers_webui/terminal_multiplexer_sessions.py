import shutil
import subprocess
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_constants import RUNNING_NAMES_LIMIT
from stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_views import MultiplexerProblem
from stackops.utils.schemas.config.multiplexer_types import SESSION_MULTIPLEXERS, SessionMultiplexer


# What is running in one multiplexer right now. `count` is None when it could not be read, and `problem` then says why. `names` holds the
# first few only.
class RunningView(TypedDict):
    name: str
    count: int | None
    names: list[str]
    problem: str


# The names the Sessions page would list for this multiplexer, read the way the CLI reads them. For Herdr those are the workspaces of its
# running session, and for AoE the sessions that are alive.
def _session_names(multiplexer: SessionMultiplexer) -> list[str]:
    match multiplexer:
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import list_session_names as list_tmux_session_names

            return list_tmux_session_names()
        case "zellij":
            from stackops.scripts.python.helpers.helpers_sessions._zellij_backend_state import list_session_names as list_zellij_session_names

            return list_zellij_session_names()
        case "tuios":
            from stackops.scripts.python.helpers.helpers_sessions._tuios_backend_state import list_session_entries as list_tuios_session_entries

            return [session.name for session in list_tuios_session_entries() if not session.saved]
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions._herdr_backend import list_killable_session_names, list_workspace_entries
            from stackops.scripts.python.helpers.helpers_sessions.herdr_export_source import workspace_display_name

            workspaces = list_workspace_entries()
            if workspaces is not None:
                return [workspace_display_name(workspace) for workspace in workspaces]
            # Herdr answers a request for its workspaces with an error while none of its sessions is running, which is nothing running and no failure.
            if list_killable_session_names(delete=False) == []:
                return []
            raise ValueError("Herdr did not list its workspaces.")
        case "aoe":
            from stackops.scripts.python.helpers.helpers_sessions._aoe_backend import list_session_entries as list_aoe_session_entries
            from stackops.scripts.python.helpers.helpers_sessions._aoe_backend import session_display_name

            sessions = list_aoe_session_entries()
            if sessions is None:
                raise ValueError("AoE did not list its sessions.")
            return [session_display_name(session) for session in sessions if session.get("running") is True]


def read_running_sessions(name: str) -> RunningView | MultiplexerProblem:
    if name not in SESSION_MULTIPLEXERS:
        return MultiplexerProblem(status=400, message=f"""`name` must be one of {", ".join(SESSION_MULTIPLEXERS)}.""")
    if shutil.which(name) is None:
        return {"name": name, "count": None, "names": [], "problem": f"""{name} is not installed."""}
    try:
        names = _session_names(multiplexer=name)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {"name": name, "count": None, "names": [], "problem": str(error)}
    return {"name": name, "count": len(names), "names": names[:RUNNING_NAMES_LIMIT], "problem": ""}
