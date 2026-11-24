from collections.abc import Callable

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.vault_file_copy import VaultCopied, copy_vault_logins, describe_copy_target
from stackops.scripts.python.helpers.helpers_webui.vault_file_fixes import VaultFixed, check_vault_file, create_vault_file, protect_vault_file, refresh_vault_schema
from stackops.scripts.python.helpers.helpers_webui.vault_file_health import read_vault_health
from stackops.scripts.python.helpers.helpers_webui.vault_form import VaultProblem

type VaultFileChange = Callable[[object], VaultFixed | VaultCopied | VaultProblem]


# What the vault file views read and change: the health of each vault file with what it holds (`devops vault validate`, `stats`), creating a
# missing one (`init`), and copying chosen logins to another file (`subset`). They read in this process with the commands' own code, since the
# commands print a table or one sentence. A file is named the way the Vault page names it: by `source`, for the folder the page works in.
# Nothing here sends or logs a value.
def vault_file_routes(working_directory: str) -> list[Route]:
    def answer(result: object) -> JSONResponse:
        match result:
            case VaultProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    def health(request: Request) -> JSONResponse:
        return answer(read_vault_health(base_directory=request.query_params.get("base", working_directory)))

    def check(request: Request) -> JSONResponse:
        return answer(check_vault_file(base_directory=request.query_params.get("base", working_directory), source=request.query_params.get("source", "")))

    def copy_target(request: Request) -> JSONResponse:
        return answer(
            describe_copy_target(
                base_directory=request.query_params.get("base", working_directory), source=request.query_params.get("source", ""), text=request.query_params.get("path", "")
            )
        )

    def changing(change: VaultFileChange) -> Callable[[Request], object]:
        async def endpoint(request: Request) -> JSONResponse:
            if request.headers.get("content-type") != "application/json":
                return JSONResponse({"error": "Send the request as application/json."}, status_code=415)
            return answer(await run_in_threadpool(change, await request.json()))

        return endpoint

    return [
        Route("/api/vault/file/health", health),
        Route("/api/vault/file/check", check),
        Route("/api/vault/file/create", changing(create_vault_file), methods=["POST"]),
        Route("/api/vault/file/schema", changing(refresh_vault_schema), methods=["POST"]),
        Route("/api/vault/file/protect", changing(protect_vault_file), methods=["POST"]),
        Route("/api/vault/file/copy/target", copy_target),
        Route("/api/vault/file/copy", changing(copy_vault_logins), methods=["POST"]),
    ]
