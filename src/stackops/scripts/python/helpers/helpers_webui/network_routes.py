from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.network_forwards import ForwardProblem, check_local_port, read_forward_hosts, read_forwards_overview, stop_forward
from stackops.scripts.python.helpers.helpers_webui.network_glance import read_network_glance
from stackops.scripts.python.helpers.helpers_webui.network_ssh_keys import KeyProblem, add_offered_keys, check_offered_keys, read_keys_overview
from stackops.scripts.python.helpers.helpers_webui.network_ssh_setup import read_setup_plan
from stackops.scripts.python.helpers.helpers_webui.network_tunnels import read_tunnels_local
from stackops.scripts.python.helpers.helpers_webui.network_tunnels_account import TunnelProblem, read_account_tunnels
from stackops.scripts.python.helpers.helpers_webui.network_warp import read_warp_overview
from stackops.scripts.python.helpers.helpers_webui.network_wifi import connect_wifi, read_wifi_nearby, read_wifi_overview, read_wifi_signal
from stackops.scripts.python.helpers.helpers_webui.network_wifi_model import WifiProblem


# What the Network page's purpose-built views read and change, all under /api/network/. Each view reads this machine in-process, through
# the helpers its CLI command uses, and asks apart for whatever takes seconds or needs the network. What changes something goes through the
# CLI's own writers (a key, a Wi-Fi network) or ends a process the page listed (a forward); everything else the views start runs as a task.
def network_routes() -> list[Route]:
    def answer(result: object) -> Response:
        match result:
            case KeyProblem() | ForwardProblem() | WifiProblem() | TunnelProblem():
                return JSONResponse({"error": result.message}, status_code=result.status)
            case _:
                return JSONResponse(result)

    def glance(_request: Request) -> Response:
        return answer(read_network_glance())

    def ssh_keys(_request: Request) -> Response:
        return answer(read_keys_overview())

    def ssh_setup(_request: Request) -> Response:
        return answer(read_setup_plan())

    async def ssh_check(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the key to check as application/json."}, status_code=415)
        result = check_offered_keys(await request.json())
        return answer(result if isinstance(result, KeyProblem) else {"keys": result})

    async def ssh_add(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the key to add as application/json."}, status_code=415)
        return answer(add_offered_keys(await request.json()))

    def forwards(_request: Request) -> Response:
        return answer(read_forwards_overview())

    def forward_hosts(_request: Request) -> Response:
        return answer({"hosts": read_forward_hosts()})

    def forward_port(request: Request) -> Response:
        return answer(check_local_port(text=request.query_params.get("port", "")))

    async def forward_stop(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the forward to stop as application/json."}, status_code=415)
        # The wait for the process to go must not hold up the server's other answers.
        return answer(await run_in_threadpool(stop_forward, await request.json()))

    def wifi(_request: Request) -> Response:
        return answer(read_wifi_overview())

    def wifi_signal(_request: Request) -> Response:
        return answer({"signal": read_wifi_signal()})

    def wifi_nearby(request: Request) -> Response:
        result = read_wifi_nearby(fresh=request.query_params.get("fresh") == "1")
        return answer(result if isinstance(result, WifiProblem) else {"networks": result})

    async def wifi_connect(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the network to join as application/json."}, status_code=415)
        return answer(await run_in_threadpool(connect_wifi, await request.json()))

    def warp(_request: Request) -> Response:
        return answer(read_warp_overview())

    def tunnels(_request: Request) -> Response:
        return answer(read_tunnels_local())

    def tunnels_account(_request: Request) -> Response:
        result = read_account_tunnels()
        return answer(result if isinstance(result, TunnelProblem) else {"tunnels": result})

    return [
        Route("/api/network/glance", glance),
        Route("/api/network/ssh/keys", ssh_keys, methods=["GET"]),
        Route("/api/network/ssh/keys", ssh_add, methods=["POST"]),
        Route("/api/network/ssh/keys/check", ssh_check, methods=["POST"]),
        Route("/api/network/ssh/setup", ssh_setup),
        Route("/api/network/forwards", forwards),
        Route("/api/network/forwards/hosts", forward_hosts),
        Route("/api/network/forwards/port", forward_port),
        Route("/api/network/forwards/stop", forward_stop, methods=["POST"]),
        Route("/api/network/wifi", wifi),
        Route("/api/network/wifi/signal", wifi_signal),
        Route("/api/network/wifi/nearby", wifi_nearby),
        Route("/api/network/wifi/connect", wifi_connect, methods=["POST"]),
        Route("/api/network/warp", warp),
        Route("/api/network/tunnels", tunnels),
        Route("/api/network/tunnels/account", tunnels_account),
    ]
