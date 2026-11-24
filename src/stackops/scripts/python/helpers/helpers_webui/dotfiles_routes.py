import time
from pathlib import Path

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.dotfiles_constants import DOTFILES_RECEIVED_NAME, DOTFILES_RECEIVED_STAMP
from stackops.scripts.python.helpers.helpers_webui.dotfiles_export_plan import read_export_plan
from stackops.scripts.python.helpers.helpers_webui.dotfiles_import_inspect import inspect_archive
from stackops.scripts.python.helpers.helpers_webui.dotfiles_import_state import read_import_state
from stackops.scripts.python.helpers.helpers_webui.dotfiles_model import DotfilesProblem, describe_archive, typed_path
from stackops.scripts.python.helpers.helpers_webui.dotfiles_register_check import check_register


# What the Dotfiles page's purpose-built views read and change, all under /api/dotfiles/. Everything here only reads, except `receive`, which
# saves an archive dropped onto the page into the home folder. Making an archive, bringing one in and adding a file are done by the CLI's own
# commands, run as tasks from the page.
def dotfiles_routes() -> list[Route]:
    def answer(result: object) -> JSONResponse:
        match result:
            case DotfilesProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    def export_plan(_request: Request) -> JSONResponse:
        return answer(read_export_plan())

    # Whether something already lies where the archive is to be saved: the export command refuses a place that is taken.
    def export_place(request: Request) -> JSONResponse:
        place = typed_path(text=request.query_params.get("path", ""), base_directory=request.query_params.get("base", ""))
        return JSONResponse({"path": str(place), "taken": place.exists() or place.is_symlink()})

    def import_state(_request: Request) -> JSONResponse:
        return answer(read_import_state())

    # Opening an archive copies or fetches it and runs GnuPG, so it must not hold up the server's other answers.
    async def import_inspect(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the archive and its password as application/json."}, status_code=415)
        return answer(await run_in_threadpool(inspect_archive, await request.json()))

    async def receive(request: Request) -> JSONResponse:
        target = Path.home().joinpath(DOTFILES_RECEIVED_NAME.format(stamp=time.strftime(DOTFILES_RECEIVED_STAMP)))
        with target.open("xb") as destination:
            async for chunk in request.stream():
                destination.write(chunk)
        if target.stat().st_size == 0:
            target.unlink()
            return JSONResponse({"error": "That file is empty."}, status_code=400)
        return JSONResponse(describe_archive(target), status_code=201)

    def register_check(request: Request) -> JSONResponse:
        asked = request.query_params
        match asked.get("method", ""):
            case "copy" | "symlink" as method if asked.get("file", "").strip() != "":
                return answer(
                    check_register(
                        {
                            "file": asked["file"],
                            "base": asked.get("base", ""),
                            "method": method,
                            "destination": asked.get("destination", ""),
                            "shared": asked.get("shared") == "1",
                            "name": asked.get("name", ""),
                            "group": asked.get("group", ""),
                            "os_filter": asked.get("os", ""),
                            "note": asked.get("note"),
                        }
                    )
                )
            case _:
                return JSONResponse({"error": "Name the file and say whether it is copied or linked."}, status_code=400)

    return [
        Route("/api/dotfiles/export/plan", export_plan),
        Route("/api/dotfiles/export/place", export_place),
        Route("/api/dotfiles/import/state", import_state),
        Route("/api/dotfiles/import/inspect", import_inspect, methods=["POST"]),
        Route("/api/dotfiles/import/receive", receive, methods=["POST"]),
        Route("/api/dotfiles/register/check", register_check),
    ]
