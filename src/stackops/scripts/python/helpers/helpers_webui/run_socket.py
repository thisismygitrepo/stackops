import asyncio

from starlette.websockets import WebSocket, WebSocketDisconnect

from stackops.scripts.python.helpers.helpers_webui.runs import Run, RunEvent, describe_run, subscribe


async def relay_run(websocket: WebSocket, run: Run) -> None:
    await websocket.accept()
    snapshot, queue = subscribe(run)
    await websocket.send_bytes(snapshot)
    if run.outcome is not None:
        await websocket.send_json(describe_run(run))

    async def forward_events() -> None:
        while True:
            event: RunEvent = await queue.get()
            if isinstance(event, bytes):
                await websocket.send_bytes(event)
            else:
                await websocket.send_json(describe_run(run))

    forwarder = asyncio.create_task(forward_events())
    try:
        while True:
            message: dict[str, object] = await websocket.receive_json()
            if run.outcome is not None:
                continue
            match message:
                case {"type": "input", "data": str() as data}:
                    run.handle.write(data.encode())
                case {"type": "resize", "rows": int() as rows, "columns": int() as columns}:
                    run.handle.resize(rows, columns)
                case _:
                    raise ValueError(f"""Unexpected terminal message: {message}""")
    except WebSocketDisconnect:
        pass
    finally:
        forwarder.cancel()
        await asyncio.gather(forwarder, return_exceptions=True)
        run.subscribers.discard(queue)
