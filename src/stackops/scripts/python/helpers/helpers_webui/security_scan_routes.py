from typing import cast

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.security_paths import resolve_typed_path
from stackops.scripts.python.helpers.helpers_webui.security_scan_export import check_export_place, export_saved_run, read_export_plan
from stackops.scripts.python.helpers.helpers_webui.security_scan_plans import ScanProblem, read_install_plan, read_run_choices


# What "Install from a scan" and "Export a scan" read and do. Both start from the saved scans, read with the helpers the scan commands use.
# Installing is the CLI command, run as a task; an export writes four small files, so it is done here and answers with what it wrote.
def security_scan_routes() -> list[Route]:
    def runs(_request: Request) -> JSONResponse:
        return JSONResponse(read_run_choices())

    def install_plan(request: Request) -> JSONResponse:
        plan = read_install_plan(run_id=request.query_params.get("run", ""))
        match plan:
            case ScanProblem():
                return JSONResponse({"error": plan.message}, status_code=plan.status)
            case _:
                return JSONResponse(plan)

    def export_plan(request: Request) -> JSONResponse:
        plan = read_export_plan(run_id=request.query_params.get("run", ""))
        match plan:
            case ScanProblem():
                return JSONResponse({"error": plan.message}, status_code=plan.status)
            case _:
                return JSONResponse(plan)

    def export_place(request: Request) -> JSONResponse:
        typed = request.query_params.get("path", "")
        if typed.strip() == "":
            return JSONResponse({"error": "Name a folder for the export."}, status_code=400)
        return JSONResponse(check_export_place(output=resolve_typed_path(typed, base_directory=request.query_params.get("base", "~"))))

    async def export(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the export as application/json."}, status_code=415)
        body: object = await request.json()
        payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
        run_id, output, base = payload.get("run"), payload.get("output"), payload.get("base")
        if not isinstance(run_id, str) or not isinstance(output, str) or output.strip() == "" or not isinstance(base, str):
            return JSONResponse({"error": "Name the scan and a folder for the export."}, status_code=400)
        outcome = await run_in_threadpool(export_saved_run, run_id, resolve_typed_path(output, base_directory=base))
        match outcome:
            case ScanProblem():
                return JSONResponse({"error": outcome.message}, status_code=outcome.status)
            case _:
                return JSONResponse(outcome)

    return [
        Route("/api/security/scans/runs", runs),
        Route("/api/security/scans/install-plan", install_plan),
        Route("/api/security/scans/export-plan", export_plan),
        Route("/api/security/scans/export-place", export_place),
        Route("/api/security/scans/export", export, methods=["POST"]),
    ]
