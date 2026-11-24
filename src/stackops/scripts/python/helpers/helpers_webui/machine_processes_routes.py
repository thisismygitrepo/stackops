from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.machine_processes_detail import ProcessProblem, read_process_detail
from stackops.scripts.python.helpers.helpers_webui.machine_processes_scan import new_scan_memory, read_processes
from stackops.scripts.python.helpers.helpers_webui.machine_processes_stop import parse_stop_request, stop_processes


# What the Processes page reads and does: every process on this machine in one reading, the rest about one of them, and stopping the chosen ones.
# The CLI command behind the page (`utils machine kill-process`) lists only what it can read in full and prints while it scans, so the page reads
# with psutil directly and reuses the command's kill. A process is named by its ID together with its start time.
def machine_processes_routes() -> list[Route]:
    memory = new_scan_memory()

    def read_list(request: Request) -> JSONResponse:
        return JSONResponse(read_processes(memory=memory, fresh=request.query_params.get("fresh") == "1"))

    def read_detail(request: Request) -> JSONResponse:
        try:
            pid = int(request.query_params.get("pid", ""))
            started = float(request.query_params.get("started", ""))
        except ValueError:
            return JSONResponse({"error": "Name the process by `pid` and `started`."}, status_code=400)
        result = read_process_detail(pid=pid, started=started)
        match result:
            case ProcessProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    async def stop(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the processes to stop as application/json."}, status_code=415)
        stop_request = parse_stop_request(await request.json())
        match stop_request:
            case ProcessProblem():
                return JSONResponse({"error": stop_request.message}, status_code=stop_request.status)
            case _:
                # The wait for the processes to go must not hold up the server's other answers.
                return JSONResponse({"results": await run_in_threadpool(stop_processes, stop_request)})

    return [
        Route("/api/machine/processes/list", read_list),
        Route("/api/machine/processes/detail", read_detail),
        Route("/api/machine/processes/stop", stop, methods=["POST"]),
    ]
