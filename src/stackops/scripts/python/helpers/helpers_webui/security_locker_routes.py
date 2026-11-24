from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.security_locker_keys import read_locker_state, read_secret_key_ids
from stackops.scripts.python.helpers.helpers_webui.security_locker_look import COMPRESSIONS, look_at
from stackops.scripts.python.helpers.helpers_webui.security_locker_run import LockerRefusal, parse_password_run, run_with_password
from stackops.scripts.python.helpers.helpers_webui.security_paths import resolve_typed_path


# What "Encrypt a file or folder" and "Decrypt a file" read and do: whether GPG is here and which keys it holds, what sits at a typed path and
# what the command would make of it, and the run itself when a password is used. A run with a key is the CLI command as a task, since GPG may
# ask for that key's own passphrase there. A password is only ever sent in the body of the one POST below.
def security_locker_routes() -> list[Route]:
    def state(_request: Request) -> JSONResponse:
        return JSONResponse({**read_locker_state(), "compressions": list(COMPRESSIONS)})

    def look(request: Request) -> JSONResponse:
        parameters = request.query_params
        mode, typed, compression = parameters.get("mode", ""), parameters.get("path", ""), parameters.get("compression", COMPRESSIONS[0])
        if mode not in ("encrypt", "decrypt") or typed.strip() == "" or compression not in COMPRESSIONS:
            return JSONResponse({"error": "Say whether to encrypt or decrypt, and which file."}, status_code=400)
        base = parameters.get("base", "~")
        output = parameters.get("output", "").strip()
        return JSONResponse(
            look_at(
                mode=mode, source=resolve_typed_path(typed, base_directory=base), compression=compression,
                output=None if output == "" else resolve_typed_path(output, base_directory=base), secret_ids=read_secret_key_ids(),
            )
        )

    async def run(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the run as application/json."}, status_code=415)
        password_run = parse_password_run(await request.json())
        match password_run:
            case LockerRefusal():
                return JSONResponse({"error": password_run.message}, status_code=400)
            case _:
                # Packing and encrypting a large folder takes a while, and must not hold up the server's other answers.
                return JSONResponse(await run_in_threadpool(run_with_password, password_run))

    return [
        Route("/api/security/locker/state", state),
        Route("/api/security/locker/look", look),
        Route("/api/security/locker/run", run, methods=["POST"]),
    ]
