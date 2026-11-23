from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.vault_form import VaultProblem
from stackops.scripts.python.helpers.helpers_webui.vault_store import delete_vault_login, read_vault_login, save_vault_login
from stackops.scripts.python.helpers.helpers_webui.vault_views import read_vault


# What the Vault page reads and changes. A login is named by the file it is in and its place there, together with the version of the file the
# page was shown. `base` is the folder the page works in, which decides where a project's own vault file is.
def vault_routes(working_directory: str) -> list[Route]:
    def problem(found: VaultProblem) -> JSONResponse:
        return JSONResponse({"error": found.message}, status_code=found.status)

    def read(request: Request) -> JSONResponse:
        result = read_vault(base_directory=request.query_params.get("base", working_directory), reveal=request.query_params.get("reveal", "hidden"))
        match result:
            case VaultProblem():
                return problem(result)
            case _:
                return JSONResponse(result)

    def read_login(request: Request) -> JSONResponse:
        result = read_vault_login(
            base_directory=request.query_params.get("base", working_directory),
            source=request.query_params.get("source", ""),
            index=request.query_params.get("index", ""),
            version=request.query_params.get("version", ""),
        )
        match result:
            case VaultProblem():
                return problem(result)
            case _:
                return JSONResponse(result)

    async def save_login(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the login as application/json."}, status_code=415)
        result = save_vault_login(body=await request.json())
        match result:
            case VaultProblem():
                return problem(result)
            case _:
                return JSONResponse(result)

    def delete_login(request: Request) -> Response:
        result = delete_vault_login(
            base_directory=request.query_params.get("base", working_directory),
            source=request.query_params.get("source", ""),
            index=request.query_params.get("index", ""),
            version=request.query_params.get("version", ""),
        )
        match result:
            case VaultProblem():
                return problem(result)
            case None:
                return Response(status_code=204)

    return [
        Route("/api/vault", read),
        Route("/api/vault/login", read_login, methods=["GET"]),
        Route("/api/vault/login", save_login, methods=["PUT"]),
        Route("/api/vault/login", delete_login, methods=["DELETE"]),
    ]
