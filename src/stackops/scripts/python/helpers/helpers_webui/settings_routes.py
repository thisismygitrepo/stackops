from typing import cast

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.settings_assets import read_assets_state
from stackops.scripts.python.helpers.helpers_webui.settings_files import (
    SettingsProblem,
    check_settings_file,
    create_settings_file,
    parse_file_kind,
    read_file_target,
    read_settings_example,
    read_settings_files,
    read_working_folder,
)
from stackops.scripts.python.helpers.helpers_webui.settings_setup import read_setup_state


# What the purpose-built settings views on the Home page read and change, all under /api/settings/. The page says which folder it works in (`base`),
# because two of the files belong to the project that folder is part of. One file is named by its `kind` and, for the kinds that have both a
# project's file and the person's own, its `scope`. The list of files answers at once; whether a file passes its check takes half a second
# and is asked for one file at a time. Edits, exports and the guided steps go through the CLI as runs.
def settings_routes() -> list[Route]:
    def answer(result: object) -> JSONResponse:
        match result:
            case SettingsProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    def read_files(request: Request) -> JSONResponse:
        folder = read_working_folder(text=request.query_params.get("base", ""))
        match folder:
            case SettingsProblem():
                return answer(folder)
            case _:
                return answer(read_settings_files(folder=folder))

    def check_file(request: Request) -> JSONResponse:
        asked = request.query_params
        target = read_file_target(kind=asked.get("kind"), scope=asked.get("scope"), base=asked.get("base"))
        match target:
            case SettingsProblem():
                return answer(target)
            case _:
                return answer(check_settings_file(target=target))

    def read_example(request: Request) -> JSONResponse:
        kind = parse_file_kind(text=request.query_params.get("kind"))
        match kind:
            case SettingsProblem():
                return answer(kind)
            case _:
                return answer(read_settings_example(kind=kind))

    async def create_file(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the file to create as application/json."}, status_code=415)
        body: object = await request.json()
        fields = cast(dict[str, object], body) if isinstance(body, dict) else {}
        target = read_file_target(kind=fields.get("kind"), scope=fields.get("scope"), base=fields.get("base"))
        match target:
            case SettingsProblem():
                return answer(target)
            case _:
                return answer(await run_in_threadpool(create_settings_file, target=target))

    def read_setup(_request: Request) -> JSONResponse:
        return JSONResponse(read_setup_state())

    def read_assets(_request: Request) -> JSONResponse:
        return JSONResponse(read_assets_state())

    return [
        Route("/api/settings/files", read_files),
        Route("/api/settings/files/check", check_file),
        Route("/api/settings/files/example", read_example),
        Route("/api/settings/files/create", create_file, methods=["POST"]),
        Route("/api/settings/setup", read_setup),
        Route("/api/settings/assets", read_assets),
    ]
