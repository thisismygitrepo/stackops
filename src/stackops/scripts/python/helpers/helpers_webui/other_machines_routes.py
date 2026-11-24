import asyncio
import ipaddress
from collections.abc import Awaitable, Callable
from typing import TypedDict, cast
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.constants import LOOPBACK_HOSTS
from stackops.scripts.python.helpers.helpers_webui.other_machines_hosts import SshHost, read_ssh_hosts
from stackops.scripts.python.helpers.helpers_webui.other_machines_links import LinkProblem, MachineLink, close_link, open_link, read_last_words
from stackops.scripts.python.helpers.helpers_webui.other_machines_marker import MachineSummary, OpenedFrom
from stackops.scripts.python.helpers.helpers_webui.other_machines_prepare import MachineStep, prepare_machine


# One machine of the SSH config as the page lists it. `there` is who answered on it while its web UI is open from here, and `problem` is how
# its last connection ended, if it ended on its own.
class MachineRow(TypedDict):
    name: str
    address: str
    there: MachineSummary | None
    problem: str | None


# Why a machine did not open, and the step the page offers to take on it before it connects again, if one would help.
class LinkRefusal(TypedDict):
    error: str
    offer: MachineStep | None


def link_answer(result: MachineLink | LinkProblem) -> JSONResponse:
    match result:
        case MachineLink():
            return JSONResponse({"address": f"""{result.address}?token={result.token}"""})
        case LinkProblem(reason="missing"):
            return JSONResponse(LinkRefusal(error=result.message, offer="install"), status_code=502)
        case LinkProblem(reason="outdated"):
            return JSONResponse(LinkRefusal(error=result.message, offer="update"), status_code=502)
        case LinkProblem():
            return JSONResponse(LinkRefusal(error=result.message, offer=None), status_code=502)


# The machine switcher at the top of the app view. Opening a machine starts its own web UI over SSH and forwards a port to it; the page then
# goes to that port, so everything it shows and runs is that machine's. `links` holds the machines open from this server.
def other_machines_routes(links: dict[str, MachineLink], here: MachineSummary, opened_from: OpenedFrom | None) -> list[Route]:
    locks: dict[str, asyncio.Lock] = {}

    # Why this server opens no machine for the browser that asks, if it does not. A tunnel ends on this machine's loopback, so only a browser on
    # this machine reaches it: not one on another device, nor one behind a proxy on this machine, whose Host is then not a loopback name. A tunnel
    # made on a machine that was itself opened from another one would end there, out of reach of the person's browser too.
    def closed_for(request: Request) -> str | None:
        if opened_from is not None:
            return f"""This page shows {here["name"]}, opened from {opened_from["name"]}. Go back there to open another machine."""
        from_loopback = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
        if not from_loopback or urlsplit(f"""http://{request.headers.get("host", "")}""").hostname not in LOOPBACK_HOSTS:
            return f"""This page is open through the network, where a browser cannot reach the tunnel to another machine. Open it at localhost on {here["name"]} to switch machines."""
        return None

    # Reading the list changes nothing, as no GET here does (`access_guard.py`). So a connection that ended on its own stays in `links` and is
    # reported as ended until the machine is opened again or disconnected.
    async def list_machines(request: Request) -> JSONResponse:
        closed = closed_for(request)
        hosts: list[SshHost] = [] if closed is not None else await asyncio.to_thread(read_ssh_hosts)
        listed = {host["name"] for host in hosts}
        # A machine that is open stays listed after its name leaves the SSH config, so that it can still be disconnected.
        hosts.extend({"name": name, "address": ""} for name in links if name not in listed)
        rows: list[MachineRow] = []
        for host in hosts:
            link = links.get(host["name"])
            if link is None:
                rows.append({"name": host["name"], "address": host["address"], "there": None, "problem": None})
            elif link.session.exit_code is None:
                rows.append({"name": host["name"], "address": host["address"], "there": link.there, "problem": None})
            else:
                ending = f"""The connection to {host["name"]} ended. {read_last_words(link.session.output)}""".rstrip()
                rows.append({"name": host["name"], "address": host["address"], "there": None, "problem": ending})
        return JSONResponse({"here": here, "closed": closed, "machines": rows})

    async def read_name(request: Request) -> str | JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the machine's name as application/json."}, status_code=415)
        body: object = await request.json()
        name = cast(dict[str, object], body).get("name") if isinstance(body, dict) else None
        if not isinstance(name, str):
            return JSONResponse({"error": "`name` must be the machine's name in the SSH config."}, status_code=400)
        return name

    async def openable_name(request: Request) -> str | JSONResponse:
        name = await read_name(request)
        if isinstance(name, JSONResponse):
            return name
        closed = closed_for(request)
        if closed is not None:
            return JSONResponse({"error": closed}, status_code=409)
        # Only a name the SSH config lists is handed to SSH, never text as it came from the page.
        if name not in links and name not in {host["name"] for host in await asyncio.to_thread(read_ssh_hosts)}:
            return JSONResponse({"error": f"""The SSH config has no machine named {name}."""}, status_code=404)
        return name

    # The address this server has in the browser that asked: where the other machine's page sends the person back.
    async def open_for(request: Request, name: str) -> MachineLink | LinkProblem:
        return await open_link(links=links, name=name, here_name=here["name"], home_address=f"""http://{request.headers.get("host", "")}/""")

    async def connect(request: Request) -> JSONResponse:
        name = await openable_name(request)
        if isinstance(name, JSONResponse):
            return name
        # One at a time for each machine, so a second press joins the connection the first one is making.
        async with locks.setdefault(name, asyncio.Lock()):
            result = await open_for(request=request, name=name)
        return link_answer(result)

    # Takes the step on the machine, then opens it. A machine the step did not make openable is not offered the same step again.
    def prepare_route(step: MachineStep) -> Callable[[Request], Awaitable[JSONResponse]]:
        async def prepare(request: Request) -> JSONResponse:
            name = await openable_name(request)
            if isinstance(name, JSONResponse):
                return name
            async with locks.setdefault(name, asyncio.Lock()):
                problem = await prepare_machine(name=name, step=step)
                result = problem if problem is not None else await open_for(request=request, name=name)
            match result:
                case LinkProblem(reason="missing"):
                    return JSONResponse(LinkRefusal(error=f"""StackOps is installed on {name}, yet an SSH command there still does not find `stackops`.""", offer=None), status_code=502)
                case LinkProblem(reason="outdated"):
                    return JSONResponse(LinkRefusal(error=f"""{name} now has the newest StackOps it can get, and that is still too old to be opened from another machine.""", offer=None), status_code=502)
                case _:
                    return link_answer(result)

        return prepare

    async def disconnect(request: Request) -> Response:
        name = await read_name(request)
        if isinstance(name, JSONResponse):
            return name
        link = links.pop(name, None)
        if link is not None:
            await close_link(link)
        return Response(status_code=204)

    return [
        Route("/api/other-machines", list_machines, methods=["GET"]),
        Route("/api/other-machines/connect", connect, methods=["POST"]),
        Route("/api/other-machines/install", prepare_route(step="install"), methods=["POST"]),
        Route("/api/other-machines/update", prepare_route(step="update"), methods=["POST"]),
        Route("/api/other-machines/disconnect", disconnect, methods=["POST"]),
    ]
