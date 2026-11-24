from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.terminal_ghostty_status import read_ghostty_status


# What the Ghostty theme sheet reads beyond what its command prints: whether Ghostty can be run here, and the theme it is set to use.
# The list of theme names and setting one go through the command itself.
def terminal_ghostty_routes() -> list[Route]:
    def status(_request: Request) -> JSONResponse:
        return JSONResponse(read_ghostty_status())

    return [Route("/api/terminal/ghostty/status", status)]
