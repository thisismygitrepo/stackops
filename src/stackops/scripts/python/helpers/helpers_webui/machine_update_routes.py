from time import time

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.machine_update_effects import read_update_effects
from stackops.scripts.python.helpers.helpers_webui.machine_update_install import ToolsFolder
from stackops.scripts.python.helpers.helpers_webui.machine_update_state import UpdateMemory, read_latest, read_update_state
from stackops.version import get_stackops_version


# What the Update StackOps page reads. Three lookups, so the page can show the first while the others are on their way: what is installed here
# (this machine alone, quick), the newest version there is (the network, kept for a while), and what the optional steps would touch.
# None of them changes anything: the update itself is the CLI command, run like any other task.
# The version is read here, when the server starts. Later the installed files can be newer than the program that is running.
def machine_update_routes() -> list[Route]:
    memory = UpdateMemory(started_at=time(), started_version=get_stackops_version(), tools=ToolsFolder(path=None), answers={})

    def state(_request: Request) -> JSONResponse:
        return JSONResponse(read_update_state(memory=memory))

    def latest(request: Request) -> JSONResponse:
        return JSONResponse(read_latest(memory=memory, fresh=request.query_params.get("fresh") == "1"))

    def effects(_request: Request) -> JSONResponse:
        return JSONResponse(read_update_effects())

    return [Route("/api/machine/update/state", state), Route("/api/machine/update/latest", latest), Route("/api/machine/update/effects", effects)]
