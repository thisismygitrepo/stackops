import time
from asyncio import Runner, sleep
from collections.abc import Generator
from dataclasses import dataclass
from typing import cast

import pytest
import vt
from aiohttp import web

from stackops.jobs.installer.checks import vt_transport


@dataclass
class _ServerState:
    payloads: list[bytes]
    authenticated: bool
    response: dict[str, object]
    status: int
    delay: float


@dataclass
class _LocalTransport:
    transport: vt_transport.VtTransport
    upload_url: str
    state: _ServerState


@pytest.fixture
def local_transport(monkeypatch: pytest.MonkeyPatch) -> Generator[_LocalTransport, None, None]:
    state = _ServerState([], False, {"data": {"type": "analysis", "id": "analysis-id", "attributes": {"status": "queued"}}}, 200, 0.0)

    async def upload(request: web.Request) -> web.Response:
        state.authenticated = request.headers.get("X-Apikey") == "dummy-secret"
        reader = await request.multipart()
        part = await reader.next()
        assert part is not None
        assert part.name == "file"
        assert part.filename == "unknown"
        state.payloads.append(bytes(await part.read(decode=False)))
        await sleep(state.delay)
        return web.json_response(state.response, status=state.status)

    async def get_file(_request: web.Request) -> web.Response:
        await sleep(state.delay)
        return web.json_response({"data": {"type": "file", "id": "file-hash", "attributes": {}}})

    application = web.Application()
    application.router.add_post("/upload", upload)
    application.router.add_get("/api/v3/files/{file_hash}", get_file)
    server = web.AppRunner(application)

    async def start() -> str:
        await server.setup()
        site = web.TCPSite(server, "127.0.0.1", 0)
        await site.start()
        hostname, port = cast(tuple[str, int], server.addresses[0])
        return f"""http://{hostname}:{port}"""

    with Runner() as runner:
        host = runner.run(start())

        def create_client(api_key: str) -> vt.Client:
            return vt.Client(api_key, host=host, timeout=60)

        monkeypatch.setattr(vt_transport, "get_vt_client", create_client)
        transport = vt_transport.VtTransport("dummy-secret")
        try:
            yield _LocalTransport(transport, f"""{host}/upload""", state)
        finally:
            transport.close()
            runner.run(server.cleanup())


def test_public_sdk_upload_sends_authenticated_multipart_exact_bytes(local_transport: _LocalTransport) -> None:
    payload = b"\x00\xffexact-file-bytes\r\n"
    response = local_transport.transport.upload_file(local_transport.upload_url, payload, time.monotonic() + 5.0)
    assert response.id == "analysis-id"
    assert response.status == "queued"
    assert local_transport.state.payloads == [payload]
    assert local_transport.state.authenticated


def test_public_sdk_upload_returns_api_error_for_error_response(local_transport: _LocalTransport) -> None:
    local_transport.state.status = 403
    local_transport.state.response = {"error": {"code": "ForbiddenError", "message": "private details"}}
    with pytest.raises(vt.APIError) as failure:
        local_transport.transport.upload_file(local_transport.upload_url, b"payload", time.monotonic() + 5.0)
    assert failure.value.code == "ForbiddenError"


def test_upload_response_rejects_invalid_analysis_data(local_transport: _LocalTransport) -> None:
    local_transport.state.response = {"data": []}
    with pytest.raises(ValueError, match="invalid analysis data"):
        local_transport.transport.upload_file(local_transport.upload_url, b"payload", time.monotonic() + 5.0)


def test_analysis_deadline_interrupts_actual_in_flight_sdk_request(local_transport: _LocalTransport) -> None:
    local_transport.state.delay = 0.05
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        local_transport.transport.get_object("/files/{}", "hash", started + 0.01)
    assert time.monotonic() - started < local_transport.state.delay
