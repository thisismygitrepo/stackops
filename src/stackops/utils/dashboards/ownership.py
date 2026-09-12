import http.client
from pathlib import Path

import psutil
from pydantic import BaseModel, ConfigDict

from stackops.utils.dashboards.constants import HEALTH_TIMEOUT_SECONDS


class DashboardOwner(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    fingerprint: str
    pid: int
    created_at: float


def read_owner(path: Path) -> DashboardOwner | None:
    if not path.exists():
        return None
    return DashboardOwner.model_validate_json(path.read_text(encoding="utf-8"))


def owner_is_alive(owner: DashboardOwner) -> bool:
    try:
        process = psutil.Process(owner.pid)
        return process.create_time() == owner.created_at and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def listener_pids(port: int) -> set[int | None]:
    connections = psutil.net_connections(kind="tcp")
    return {
        connection.pid for connection in connections
        if connection.status == psutil.CONN_LISTEN and connection.laddr and connection.laddr.port == port
    }


def owner_is_healthy(owner: DashboardOwner, port: int, health_path: str) -> bool:
    if not owner_is_alive(owner) or listener_pids(port) != {owner.pid}:
        return False
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=HEALTH_TIMEOUT_SECONDS)
    try:
        connection.request("GET", health_path)
        response = connection.getresponse()
        return response.status == 200 and owner_is_alive(owner) and listener_pids(port) == {owner.pid}
    except (OSError, http.client.HTTPException):
        return False
    finally:
        connection.close()
