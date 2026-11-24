from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_items import BitwardenProblem, read_bitwarden_items, read_bitwarden_value
from stackops.scripts.python.helpers.helpers_webui.vault_bitwarden_state import read_bitwarden_place, read_bitwarden_state

# A value on its way to the page is not to be kept by anything in between.
NOT_KEPT = {"Cache-Control": "no-store"}


# What the Bitwarden page reads beyond what the commands print: how `bw` stands, the items by label, and one value when the person asks for it.
# Unlock, Sync and Clear the cache are the commands themselves, run by the page. The search word and an item's ID travel in a request body, so
# neither is ever part of an address, and nothing here logs.
def vault_bitwarden_routes() -> list[Route]:
    def problem(found: BitwardenProblem) -> JSONResponse:
        return JSONResponse({"error": found.message, "reason": found.reason}, status_code=found.status, headers=NOT_KEPT)

    def place(_request: Request) -> JSONResponse:
        return JSONResponse(read_bitwarden_place())

    def state(_request: Request) -> JSONResponse:
        return JSONResponse(read_bitwarden_state(), headers=NOT_KEPT)

    async def items(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the request as application/json."}, status_code=415)
        body: object = await request.json()
        result = await run_in_threadpool(read_bitwarden_items, isinstance(body, dict) and body.get("fresh") is True)
        match result:
            case BitwardenProblem():
                return problem(result)
            case _:
                return JSONResponse(result, headers=NOT_KEPT)

    async def value(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the request as application/json."}, status_code=415)
        result = await run_in_threadpool(read_bitwarden_value, await request.json())
        match result:
            case BitwardenProblem():
                return problem(result)
            case _:
                return JSONResponse(result, headers=NOT_KEPT)

    return [
        Route("/api/vault/bitwarden/place", place),
        Route("/api/vault/bitwarden/state", state),
        Route("/api/vault/bitwarden/items", items, methods=["POST"]),
        Route("/api/vault/bitwarden/value", value, methods=["POST"]),
    ]
