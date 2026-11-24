import subprocess
import sys

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.machine_windows_actions import apply_window_action
from stackops.scripts.python.helpers.helpers_webui.machine_windows_constants import ACCESSIBILITY_SETTINGS_ADDRESS, OPEN_SETTINGS_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_webui.machine_windows_listing import read_windows
from stackops.scripts.python.helpers.helpers_webui.machine_windows_models import WindowsProblem


# What the Windows page reads and does. The list and the actions come from the helpers the `utils machine window` command itself uses, called
# in this process: the command prints neither where a window is nor why a machine cannot list its windows, and starting it once per click would
# make every button wait for Python to start. Asking a desktop for its windows takes a moment, so none of it runs on the server's own loop.
def machine_windows_routes() -> list[Route]:
    def answer(result: object) -> JSONResponse:
        match result:
            case WindowsProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    def read(_request: Request) -> JSONResponse:
        return answer(read_windows())

    async def act(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the action as application/json."}, status_code=415)
        return answer(await run_in_threadpool(apply_window_action, body=await request.json()))

    # Opens System Settings on the page where macOS lists the apps it lets see and move windows. It shows on the serving machine's own screen.
    def open_permission_settings(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the request as application/json."}, status_code=415)
        if sys.platform != "darwin":
            return JSONResponse({"error": "Only macOS keeps a permission for this."}, status_code=404)
        try:
            subprocess.run(["/usr/bin/open", ACCESSIBILITY_SETTINGS_ADDRESS], check=True, capture_output=True, timeout=OPEN_SETTINGS_TIMEOUT_SECONDS)
        except (subprocess.SubprocessError, OSError) as error:
            return JSONResponse({"error": f"""System Settings did not open: {error}"""}, status_code=502)
        return Response(status_code=204)

    return [
        Route("/api/machine/windows", read, methods=["GET"]),
        Route("/api/machine/windows/action", act, methods=["POST"]),
        Route("/api/machine/windows/permission", open_permission_settings, methods=["POST"]),
    ]
