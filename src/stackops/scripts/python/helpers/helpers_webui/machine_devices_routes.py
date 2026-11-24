from collections.abc import Callable
from dataclasses import asdict
from typing import cast

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.machine_devices_actions import eject_disk, mount_volume, unmount_volume
from stackops.scripts.python.helpers.helpers_webui.machine_devices_model import ProblemReason, StorageProblem
from stackops.scripts.python.helpers.helpers_webui.machine_devices_mounts import read_mounted, storage_mark
from stackops.scripts.python.helpers.helpers_webui.machine_devices_read import read_storage

PROBLEM_STATUS: dict[ProblemReason, int] = {"unsupported": 501, "tool_missing": 501, "refused": 403, "unknown_device": 404, "failed": 409}
ACTIONS: dict[str, Callable[[str], StorageProblem | None]] = {"mount": mount_volume, "unmount": unmount_volume, "eject": eject_disk}


# What the Storage devices page reads and does. Reading goes through the same helpers as `utils machine list-devices` and `mount`, plus what
# the system says about each disk beyond that. A system whose disks cannot be listed at all answers with `unavailable` and the reason, which
# the page shows in place of the list. Unmounting and ejecting have no command, so they are done here.
def machine_devices_routes() -> list[Route]:
    def read(_request: Request) -> JSONResponse:
        picture = read_storage()
        match picture:
            case StorageProblem(reason="failed"):
                return JSONResponse({"error": picture.message}, status_code=500)
            case StorageProblem():
                return JSONResponse({"unavailable": asdict(picture)})
            case _:
                return JSONResponse(picture)

    def mark(_request: Request) -> JSONResponse:
        return JSONResponse({"mark": storage_mark(read_mounted())})

    async def act(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the device as application/json."}, status_code=415)
        body = await request.json()
        identifier = cast(dict[str, object], body).get("id") if isinstance(body, dict) else None
        action = ACTIONS.get(request.path_params["action"])
        if action is None or not isinstance(identifier, str):
            return JSONResponse({"error": "Name what to do and the device to do it to."}, status_code=400)
        problem = await run_in_threadpool(action, identifier)
        if problem is not None:
            return JSONResponse({"error": problem.message}, status_code=PROBLEM_STATUS[problem.reason])
        return Response(status_code=204)

    return [
        Route("/api/machine/devices", read),
        Route("/api/machine/devices/mark", mark),
        Route("/api/machine/devices/{action}", act, methods=["POST"]),
    ]
