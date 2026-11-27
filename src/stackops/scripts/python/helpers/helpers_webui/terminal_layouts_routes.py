from pathlib import Path
from typing import cast

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.utils.schemas.layouts.layout_enabled_edit import LayoutSwitchFailureReason, LayoutSwitchTarget, switch_layout_entry

FAILURE_STATUS: dict[LayoutSwitchFailureReason, int] = {"invalid_file": 409, "entry_gone": 409, "unsupported_format": 422}


# What the saved layouts on the Sessions page change beyond what `terminal list` prints: switching a layout, one of its tabs or one pane of
# a tab off and back on, which has no command. The file is the one the list named for the layout. Only a file that reads as a layout file
# is changed, and only its `enabled` value for that one entry.
def terminal_layouts_routes() -> list[Route]:
    async def switch(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the entry as application/json."}, status_code=415)
        body = await request.json()
        fields = cast(dict[str, object], body) if isinstance(body, dict) else {}
        file, layout, tab_index, tab_name, pane, enabled = (fields.get(name) for name in ("file", "layout", "tab_index", "tab_name", "pane", "enabled"))
        if not isinstance(file, str) or not isinstance(layout, str) or not isinstance(enabled, bool):
            return JSONResponse({"error": "Name the layout file, the layout, and whether it is on."}, status_code=400)
        if not (tab_index is None and tab_name is None and pane is None) and not (isinstance(tab_index, int) and tab_index >= 0 and isinstance(tab_name, str) and isinstance(pane, str | None)):
            return JSONResponse({"error": "Name a tab by its place and its name, and a pane by its name inside a tab."}, status_code=400)
        target = LayoutSwitchTarget(layout_name=layout, tab_index=tab_index, tab_name=tab_name, pane_name=pane)
        failure = await run_in_threadpool(switch_layout_entry, Path(file), target, enabled)
        return JSONResponse({"error": failure.message}, status_code=FAILURE_STATUS[failure.reason]) if failure is not None else Response(status_code=204)

    return [Route("/api/terminal/layouts/enabled", switch, methods=["POST"])]
