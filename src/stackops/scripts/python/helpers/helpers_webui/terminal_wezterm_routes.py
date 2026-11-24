from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.terminal_wezterm_settings import WeztermProblem, apply_scheme, read_state


# What the WezTerm theme sheet reads and changes: where the theme stands on this machine, and one theme applied by name.
# Applying goes through the command's own function in this process and not through a run, so a pick takes effect without the wait for a
# program to start. The picker itself is a run like any other.
def terminal_wezterm_routes() -> list[Route]:
    def state(_request: Request) -> JSONResponse:
        return JSONResponse(read_state())

    async def apply(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the theme as application/json."}, status_code=415)
        result = apply_scheme(body=await request.json())
        match result:
            case WeztermProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    return [
        Route("/api/terminal/wezterm/state", state),
        Route("/api/terminal/wezterm/apply", apply, methods=["POST"]),
    ]
