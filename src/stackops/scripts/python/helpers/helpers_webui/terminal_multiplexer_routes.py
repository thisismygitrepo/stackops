from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_sessions import read_running_sessions
from stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_store import save_multiplexer_default
from stackops.scripts.python.helpers.helpers_webui.terminal_multiplexer_views import MultiplexerProblem, read_multiplexer_overview


# What the Multiplexer page reads and changes. The overview answers at once; what is running in each multiplexer is asked for one at a time,
# so a slow or stuck one holds back only its own card. Saving goes through the CLI's own writer, without a run to watch.
def terminal_multiplexer_routes() -> list[Route]:
    def answer(result: object) -> Response:
        match result:
            case MultiplexerProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case None:
                return Response(status_code=204)
            case _:
                return JSONResponse(result)

    def read(_request: Request) -> Response:
        return answer(read_multiplexer_overview())

    def read_sessions(request: Request) -> Response:
        return answer(read_running_sessions(name=request.query_params.get("name", "")))

    async def save_default(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the choice as application/json."}, status_code=415)
        return answer(save_multiplexer_default(body=await request.json()))

    return [
        Route("/api/terminal/multiplexer", read),
        Route("/api/terminal/multiplexer/sessions", read_sessions),
        Route("/api/terminal/multiplexer/default", save_default, methods=["PUT"]),
    ]
