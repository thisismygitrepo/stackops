import json
import subprocess
from dataclasses import dataclass
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_webui.network_constants import CLOUDFLARED_ACCOUNT_SECONDS
from stackops.scripts.python.helpers.helpers_webui.network_tunnels import find_binary


@dataclass(frozen=True, slots=True)
class TunnelProblem:
    status: int
    message: str


# One connection a running copy of a tunnel holds to Cloudflare: the data centre it reaches and when it was opened.
class TunnelConnection(TypedDict):
    place: str
    opened_at: str


class AccountTunnel(TypedDict):
    id: str
    name: str
    created_at: str
    connections: list[TunnelConnection]


# Every tunnel of the Cloudflare account this machine is signed in to, with the connections each one holds right now. It is one question
# to Cloudflare, so it needs the network and the sign-in, and it is asked apart from what the machine itself knows.
def read_account_tunnels() -> list[AccountTunnel] | TunnelProblem:
    binary = find_binary()
    if binary == "":
        return TunnelProblem(status=409, message="cloudflared is not installed on this machine.")
    try:
        result = subprocess.run([binary, "tunnel", "list", "--output", "json"], capture_output=True, text=True, check=False, timeout=CLOUDFLARED_ACCOUNT_SECONDS, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return TunnelProblem(status=504, message=f"""Cloudflare did not answer within {CLOUDFLARED_ACCOUNT_SECONDS:g} seconds.""")
    except OSError as error:
        return TunnelProblem(status=502, message=f"""cloudflared could not be started: {error}""")
    if result.returncode != 0:
        lines = [line.strip() for line in result.stderr.splitlines() if line.strip() != ""]
        return TunnelProblem(status=502, message=lines[-1] if lines else f"""cloudflared stopped with code {result.returncode}.""")
    try:
        loaded: object = json.loads(result.stdout)
    except ValueError:
        return TunnelProblem(status=502, message="cloudflared answered with something that is not a list of tunnels.")
    tunnels: list[AccountTunnel] = []
    for item in cast(list[object], loaded) if isinstance(loaded, list) else []:
        fields = cast(dict[str, object], item) if isinstance(item, dict) else {}
        listed = fields.get("connections")
        connections: list[TunnelConnection] = [
            {"place": str(cast(dict[str, object], connection).get("colo_name", "")), "opened_at": str(cast(dict[str, object], connection).get("opened_at", ""))}
            for connection in (cast(list[object], listed) if isinstance(listed, list) else [])
            if isinstance(connection, dict)
        ]
        tunnels.append({"id": str(fields.get("id", "")), "name": str(fields.get("name", "")), "created_at": str(fields.get("created_at", "")), "connections": connections})
    return sorted(tunnels, key=lambda tunnel: (len(tunnel["connections"]) == 0, tunnel["name"].lower()))
