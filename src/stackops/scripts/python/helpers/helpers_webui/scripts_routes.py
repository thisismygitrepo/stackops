from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.scripts_files import ScriptProblem, create_script, read_script_text, read_scripts
from stackops.scripts.python.helpers.helpers_webui.scripts_online import OnlineScripts, read_online_script_text, read_online_scripts


# What the Scripts page reads: the scripts in each place the CLI looks in, the ones kept online, and the text of one. A script is named by its
# place and its path inside it. `base` is the folder the page works in, which decides where a project's own scripts are.
# Running and editing a script go through the CLI like any other run. Reading does not, because no command prints a script's text.
def scripts_routes(working_directory: str) -> list[Route]:
    online = OnlineScripts(read_at=0.0, names=[])

    def answer(result: object) -> JSONResponse:
        match result:
            case ScriptProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    def read(request: Request) -> JSONResponse:
        return answer(read_scripts(base_directory=request.query_params.get("base", working_directory)))

    def read_online(_request: Request) -> JSONResponse:
        return answer(read_online_scripts(known=online))

    def read_text(request: Request) -> JSONResponse:
        source = request.query_params.get("source", "")
        name = request.query_params.get("name", "")
        if source == "dynamic":
            return answer(read_online_script_text(known=online, name=name))
        return answer(read_script_text(base_directory=request.query_params.get("base", working_directory), source=source, name=name))

    async def create(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the script as application/json."}, status_code=415)
        return answer(create_script(body=await request.json()))

    return [
        Route("/api/scripts", read, methods=["GET"]),
        Route("/api/scripts", create, methods=["POST"]),
        Route("/api/scripts/online", read_online),
        Route("/api/scripts/text", read_text),
    ]
