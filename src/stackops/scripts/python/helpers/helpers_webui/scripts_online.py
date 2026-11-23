import time
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from stackops.scripts.python.helpers.helpers_devops.script_discovery import list_dynamic_script_names
from stackops.scripts.python.helpers.helpers_devops.script_sources import get_script_locations
from stackops.scripts.python.helpers.helpers_webui.constants import ONLINE_SCRIPT_TIMEOUT_SECONDS, ONLINE_SCRIPTS_CACHE_SECONDS, ONLINE_SCRIPTS_RAW_ROOT
from stackops.scripts.python.helpers.helpers_webui.scripts_files import ScriptProblem, ScriptText


# The names GitHub last gave, and when. `read_at` starts at zero, which is longer ago than the list is kept for.
@dataclass
class OnlineScripts:
    read_at: float
    names: list[str]


class OnlineScriptView(TypedDict):
    name: str
    path: str
    suffix: str


class OnlineScriptsView(TypedDict):
    path: str
    scripts: list[OnlineScriptView]


# The scripts `devops scripts run --source dynamic` fetches from the StackOps repository. Nothing here is on this machine until one is run.
def read_online_scripts(known: OnlineScripts) -> OnlineScriptsView | ScriptProblem:
    import requests

    if time.time() - known.read_at > ONLINE_SCRIPTS_CACHE_SECONDS:
        try:
            known.names = list_dynamic_script_names()
        except requests.RequestException as error:
            return ScriptProblem(status=502, message=f"""The scripts kept online could not be listed: {error}""")
        known.read_at = time.time()
    scripts: list[OnlineScriptView] = [{"name": name, "path": f"""{ONLINE_SCRIPTS_RAW_ROOT}/{name}""", "suffix": Path(name).suffix} for name in known.names]
    return {"path": str(get_script_locations(source="dynamic")["dynamic"]), "scripts": scripts}


def read_online_script_text(known: OnlineScripts, name: str) -> ScriptText | ScriptProblem:
    import requests

    # Only a name GitHub listed is asked for, so the page cannot have another address fetched.
    if name not in known.names:
        return ScriptProblem(status=404, message=f"""{name} is not one of the scripts kept online.""")
    try:
        response = requests.get(f"""{ONLINE_SCRIPTS_RAW_ROOT}/{name}""", timeout=ONLINE_SCRIPT_TIMEOUT_SECONDS)
        response.raise_for_status()
    except requests.RequestException as error:
        return ScriptProblem(status=502, message=f"""{name} could not be fetched: {error}""")
    return {"text": response.text}
