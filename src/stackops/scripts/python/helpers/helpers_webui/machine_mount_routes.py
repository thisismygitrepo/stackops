from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.machine_mount_devices import read_mount_picture
from stackops.scripts.python.helpers.helpers_webui.machine_mount_model import MountProblem
from stackops.scripts.python.helpers.helpers_webui.machine_mount_places import check_mount_place


# What the Mount a device page reads: the devices as the command lists them, each with whether and how it can be mounted here, and what a
# typed mount point or key file names. Mounting itself goes through the CLI as a run in the Activity panel, where a password can be typed.
def machine_mount_routes() -> list[Route]:
    def answer(result: object) -> JSONResponse:
        match result:
            case MountProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    def read_devices(_request: Request) -> JSONResponse:
        return answer(read_mount_picture())

    def read_place(request: Request) -> JSONResponse:
        return answer(
            check_mount_place(
                text=request.query_params.get("path", ""), base_directory=request.query_params.get("base", str(Path.home())), kind=request.query_params.get("kind", "folder")
            )
        )

    return [
        Route("/api/machine/mount/devices", read_devices),
        Route("/api/machine/mount/place", read_place),
    ]
