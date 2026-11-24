from typing import cast

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.security_cloud_state import read_cloud_reach, read_cloud_state, read_upload_plan
from stackops.scripts.python.helpers.helpers_webui.security_drive_link import check_drive_link, read_download_place
from stackops.scripts.python.helpers.helpers_webui.security_paths import resolve_typed_path


# What "Upload a file to cloud storage" and "Download from Google Drive" read. None of these changes anything: the upload and the download are
# the CLI commands, run as tasks. Two of them go over the network and are asked for apart from the rest: whether the cloud answers, and what
# Google Drive says about a pasted link. The link comes in a request body, since it lets whoever holds it fetch the file.
def security_cloud_routes() -> list[Route]:
    def state(_request: Request) -> JSONResponse:
        return JSONResponse(read_cloud_state())

    def reach(_request: Request) -> JSONResponse:
        cloud = read_cloud_state()
        if cloud["problem"] is not None:
            return JSONResponse({"error": "No cloud storage is set up."}, status_code=409)
        return JSONResponse(read_cloud_reach(name=cloud["name"]))

    def upload_plan(request: Request) -> JSONResponse:
        typed = request.query_params.get("path", "")
        if typed.strip() == "":
            return JSONResponse({"error": "Name a file to upload."}, status_code=400)
        return JSONResponse(read_upload_plan(path=resolve_typed_path(typed, base_directory=request.query_params.get("base", "~"))))

    def download_place(_request: Request) -> JSONResponse:
        return JSONResponse(read_download_place())

    async def drive_link(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the link as application/json."}, status_code=415)
        body: object = await request.json()
        text = cast(dict[str, object], body).get("text") if isinstance(body, dict) else None
        if not isinstance(text, str) or text.strip() == "":
            return JSONResponse({"error": "Paste a link or a file ID."}, status_code=400)
        return JSONResponse(await run_in_threadpool(check_drive_link, text))

    return [
        Route("/api/security/cloud/state", state),
        Route("/api/security/cloud/reach", reach),
        Route("/api/security/cloud/upload-plan", upload_plan),
        Route("/api/security/cloud/download-place", download_place),
        Route("/api/security/cloud/drive-link", drive_link, methods=["POST"]),
    ]
