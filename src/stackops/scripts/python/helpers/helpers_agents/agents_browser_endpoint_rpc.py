from itertools import count
import json
from typing import Final, cast

from websockets.sync.connection import Connection

_REQUEST_IDS: Final = count(1)


def call_browser_endpoint(*, connection: Connection, method: str, params: dict[str, object], timeout_seconds: float) -> dict[str, object]:
    request_id = next(_REQUEST_IDS)
    connection.send(json.dumps({"id": request_id, "method": method, "params": params}))
    while True:
        reply = cast(dict[str, object], json.loads(connection.recv(timeout=timeout_seconds)))
        if reply.get("id") == request_id:
            return reply
