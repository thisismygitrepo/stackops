import platform
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_network.warp_status import WARP_STATE, read_warp_status
from stackops.scripts.python.helpers.helpers_webui.network_constants import WARP_COMMAND, WARP_STATUS_SECONDS

# What the page shows: the states `warp-cli` reports, and two of its own for a machine without it and one whose answer did not come.
type WarpStanding = WARP_STATE | Literal["not_installed", "unreadable"]

# Systems the CLI's installer has a recipe for (`jobs/installer/python_scripts/cloudflare_warp_cli.py`).
INSTALLABLE_SYSTEMS = frozenset({"Linux", "Darwin"})


class WarpOverview(TypedDict):
    standing: WarpStanding
    detail: str
    installable: bool
    system: str


# One reading of WARP through the CLI's own reader, which asks `warp-cli` for its status. Reading it never connects or disconnects anything.
def read_warp_overview() -> WarpOverview:
    system = platform.system()
    overview: WarpOverview = {"standing": "not_installed", "detail": "", "installable": system in INSTALLABLE_SYSTEMS, "system": "macOS" if system == "Darwin" else system}
    if shutil.which(WARP_COMMAND) is None:
        return overview
    # A WARP whose background service hangs keeps its command waiting. The wait is cut short here, and the reading is left to end by itself.
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        status = pool.submit(read_warp_status).result(timeout=WARP_STATUS_SECONDS)
    except FutureTimeoutError:
        return {**overview, "standing": "unreadable", "detail": f"""{WARP_COMMAND} did not answer within {WARP_STATUS_SECONDS:g} seconds."""}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {**overview, "standing": "unreadable", "detail": str(error)}
    finally:
        pool.shutdown(wait=False)
    return {**overview, "standing": status.state, "detail": status.detail or ""}
