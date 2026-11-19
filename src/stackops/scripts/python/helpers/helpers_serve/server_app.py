import getpass
import platform
import re
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.types import ASGIApp
from starlette.websockets import WebSocket

from stackops.scripts.python.helpers.helpers_serve.access_guard import guard_access
from stackops.scripts.python.helpers.helpers_serve.capture import CaptureResult, CaptureTimeout, capture_command
from stackops.scripts.python.helpers.helpers_serve.catalog import ParameterSpec, load_command_parameters, load_command_tree
from stackops.scripts.python.helpers.helpers_serve.pages import APP_PAGE, DEVELOPER_PAGE
from stackops.scripts.python.helpers.helpers_serve.run_requests import (
    CaptureRequest,
    RequestProblem,
    RunRequest,
    parse_capture_request,
    parse_run_request,
    suggest_paths,
)
from stackops.scripts.python.helpers.helpers_serve.run_socket import relay_run
from stackops.scripts.python.helpers.helpers_serve.runs import RunRegistry, describe_run, shutdown_runs, start_run, stop_run
from stackops.scripts.python.helpers.helpers_serve.software_catalog import load_software_catalog
from stackops.scripts.python.helpers.helpers_serve.vendor_assets import VENDOR_ASSETS, resolve_vendor_asset
from stackops.utils.source_of_truth import HTML_REPORTS_ROOT
from stackops.version import get_stackops_version

WEB_ASSETS_ROOT = Path(__file__).with_name("web_assets")
REPORT_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+\.html")


def create_app(token: str, cookie_name: str, stackops_executable: str, working_directory: str) -> ASGIApp:
    registry = RunRegistry(stackops_executable=stackops_executable, runs={}, pump_threads={})
    tree, sources = load_command_tree()
    parameter_cache: dict[str, list[ParameterSpec] | None] = {}
    system_name = platform.system()
    bootstrap_payload = {
        "version": get_stackops_version(),
        "user": getpass.getuser(),
        "host": socket.gethostname(),
        "platform": "macOS" if system_name == "Darwin" else system_name,
        "home": str(Path.home()),
        "working_directory": working_directory,
        "tree": tree,
    }

    async def index(_request: Request) -> HTMLResponse:
        return HTMLResponse(APP_PAGE)

    async def developer_index(_request: Request) -> HTMLResponse:
        return HTMLResponse(DEVELOPER_PAGE)

    async def bootstrap(_request: Request) -> JSONResponse:
        return JSONResponse(bootstrap_payload)

    def command_detail(request: Request) -> JSONResponse:
        path = request.query_params.get("path", "")
        source = sources.get(path)
        if source is None:
            return JSONResponse({"error": f"""Unknown command: {path}"""}, status_code=404)
        if path not in parameter_cache:
            parameter_cache[path] = load_command_parameters(source)
        return JSONResponse({"path": path, "parameters": parameter_cache[path]})

    def list_paths(request: Request) -> JSONResponse:
        entries = suggest_paths(prefix=request.query_params.get("prefix", ""), base_directory=request.query_params.get("base", working_directory))
        return JSONResponse({"entries": entries})

    async def list_runs(_request: Request) -> JSONResponse:
        return JSONResponse({"runs": [describe_run(run) for run in registry.runs.values()]})

    async def create_run(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the run request as application/json."}, status_code=415)
        run_request = parse_run_request(await request.json())
        match run_request:
            case RequestProblem():
                return JSONResponse({"error": run_request.message}, status_code=400)
            case RunRequest():
                run = start_run(
                    registry=registry,
                    arguments=run_request.arguments,
                    working_directory=run_request.working_directory,
                    rows=run_request.rows,
                    columns=run_request.columns,
                    interactive=run_request.interactive,
                )
                return JSONResponse(describe_run(run), status_code=201)

    async def capture(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the capture request as application/json."}, status_code=415)
        capture_request = parse_capture_request(await request.json())
        match capture_request:
            case RequestProblem():
                return JSONResponse({"error": capture_request.message}, status_code=400)
            case CaptureRequest():
                result = await capture_command(
                    executable=stackops_executable,
                    arguments=capture_request.arguments,
                    working_directory=capture_request.working_directory,
                    receive=request.receive,
                )
        match result:
            case CaptureTimeout():
                return JSONResponse({"error": f"""This took longer than {result.seconds:.0f} seconds and was stopped."""}, status_code=504)
            case CaptureResult():
                return JSONResponse({"exit_code": result.exit_code, "stdout": result.stdout, "stderr": result.stderr})

    def software(_request: Request) -> JSONResponse:
        catalog = load_software_catalog()
        return JSONResponse(catalog, status_code=422 if "error" in catalog else 200)

    async def stop_run_endpoint(request: Request) -> Response:
        run = registry.runs.get(request.path_params["run_id"])
        if run is None:
            return JSONResponse({"error": "Unknown run."}, status_code=404)
        stop_run(run)
        return Response(status_code=204)

    async def delete_run(request: Request) -> Response:
        run = registry.runs.pop(request.path_params["run_id"], None)
        if run is None:
            return JSONResponse({"error": "Unknown run."}, status_code=404)
        registry.pump_threads.pop(run.run_id)
        stop_run(run)
        return Response(status_code=204)

    async def run_socket(websocket: WebSocket) -> None:
        run = registry.runs.get(websocket.path_params["run_id"])
        if run is None:
            await websocket.close(code=4404)
            return
        await relay_run(websocket=websocket, run=run)

    def report_file(request: Request) -> Response:
        name: str = request.path_params["name"]
        report_path = HTML_REPORTS_ROOT / name
        if REPORT_NAME_PATTERN.fullmatch(name) is None or not report_path.is_file():
            return Response(status_code=404)
        return FileResponse(report_path, media_type="text/html")

    def vendor_file(request: Request) -> Response:
        name: str = request.path_params["name"]
        if name not in VENDOR_ASSETS:
            return Response(status_code=404)
        asset = VENDOR_ASSETS[name]
        headers = {"Cache-Control": "no-cache", "ETag": f'''"{asset.sha384}"'''}
        if request.headers.get("if-none-match") == headers["ETag"]:
            return Response(status_code=304, headers=headers)
        return FileResponse(resolve_vendor_asset(name), media_type=asset.media_type, headers=headers)

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncGenerator[None]:
        yield
        await shutdown_runs(registry)

    app = Starlette(
        routes=[
            Route("/", index),
            Route("/dev", developer_index),
            Route("/api/bootstrap", bootstrap),
            Route("/api/command", command_detail),
            Route("/api/paths", list_paths),
            Route("/api/capture", capture, methods=["POST"]),
            Route("/api/software", software),
            Route("/api/runs", list_runs, methods=["GET"]),
            Route("/api/runs", create_run, methods=["POST"]),
            Route("/api/runs/{run_id}/stop", stop_run_endpoint, methods=["POST"]),
            Route("/api/runs/{run_id}", delete_run, methods=["DELETE"]),
            WebSocketRoute("/ws/runs/{run_id}", run_socket),
            Route("/reports/{name}", report_file),
            Route("/vendor/{name}", vendor_file),
            Mount("/assets", app=StaticFiles(directory=WEB_ASSETS_ROOT)),
        ],
        lifespan=lifespan,
    )
    return guard_access(app=app, token=token, cookie_name=cookie_name)
