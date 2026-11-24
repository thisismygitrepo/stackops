import asyncio
from typing import TypedDict, cast

from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_webui.other_machines_hosts import SshHost, read_ssh_hosts
from stackops.scripts.python.helpers.helpers_webui.other_machines_links import LinkProblem, MachineLink, close_link, open_link, read_last_words
from stackops.scripts.python.helpers.helpers_webui.other_machines_marker import MachineSummary, OpenedFrom


# One machine of the SSH config as the page lists it. `there` is who answered on it while its web UI is open from here, and `problem` is how a
# connection that ended on its own ended, told once.
class MachineRow(TypedDict):
    name: str
    address: str
    there: MachineSummary | None
    problem: str | None


# The machine switcher at the top of the app view. Opening a machine starts its own web UI over SSH and forwards a port to it; the page then
# goes to that port, so everything it shows and runs is that machine's. `links` holds the machines open from this server.
def other_machines_routes(links: dict[str, MachineLink], here: MachineSummary, opened_from: OpenedFrom | None, on_loopback: bool) -> list[Route]:
    locks: dict[str, asyncio.Lock] = {}
    endings: dict[str, str] = {}
    # Why this server opens no machines, if it does not. A tunnel made on a machine that was itself opened from another one would end there,
    # out of reach of the person's browser, and so would one made by a server that is used from another device.
    if opened_from is not None:
        closed: str | None = f"""This page shows {here["name"]}, opened from {opened_from["name"]}. Go back there to open another machine."""
    elif not on_loopback:
        closed = "This server listens on the network, where a browser cannot reach the tunnel to another machine. Start it without --host to switch machines here."
    else:
        closed = None

    async def list_machines(_request: Request) -> JSONResponse:
        for name, link in list(links.items()):
            if link.session.exit_code is not None:
                del links[name]
                endings[name] = f"""The connection to {name} ended. {read_last_words(link.session.output)}""".rstrip()
        hosts: list[SshHost] = [] if closed is not None else await asyncio.to_thread(read_ssh_hosts)
        listed = {host["name"] for host in hosts}
        # A machine that is open stays listed after its name leaves the SSH config, so that it can still be disconnected.
        hosts.extend({"name": name, "address": ""} for name in links if name not in listed)
        rows: list[MachineRow] = [
            {"name": host["name"], "address": host["address"], "there": links[host["name"]].there if host["name"] in links else None, "problem": endings.pop(host["name"], None)}
            for host in hosts
        ]
        return JSONResponse({"here": here, "closed": closed, "machines": rows})

    async def read_name(request: Request) -> str | JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the machine's name as application/json."}, status_code=415)
        body: object = await request.json()
        name = cast(dict[str, object], body).get("name") if isinstance(body, dict) else None
        if not isinstance(name, str):
            return JSONResponse({"error": "`name` must be the machine's name in the SSH config."}, status_code=400)
        return name

    async def connect(request: Request) -> JSONResponse:
        name = await read_name(request)
        if isinstance(name, JSONResponse):
            return name
        if closed is not None:
            return JSONResponse({"error": closed}, status_code=409)
        # Only a name the SSH config lists is handed to SSH, never text as it came from the page.
        if name not in links and name not in {host["name"] for host in await asyncio.to_thread(read_ssh_hosts)}:
            return JSONResponse({"error": f"""The SSH config has no machine named {name}."""}, status_code=404)
        # One at a time for each machine, so a second press joins the connection the first one is making.
        async with locks.setdefault(name, asyncio.Lock()):
            # The address this server has in the browser that asked: where the other machine's page sends the person back.
            result = await open_link(links=links, name=name, here_name=here["name"], home_address=f"""http://{request.headers.get("host", "")}/""")
        match result:
            case LinkProblem():
                return JSONResponse({"error": result.message}, status_code=502)
            case MachineLink():
                return JSONResponse({"address": f"""{result.address}?token={result.token}"""})

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
        Route("/api/other-machines/disconnect", disconnect, methods=["POST"]),
    ]
