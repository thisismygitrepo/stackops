import subprocess
import sys
from typing import cast

from stackops.scripts.python.helpers.helpers_webui.machine_windows_constants import ACCESSIBILITY_REFUSAL, ACTION_BATCH_LIMIT
from stackops.scripts.python.helpers.helpers_webui.machine_windows_listing import collect_open_windows
from stackops.scripts.python.helpers.helpers_webui.machine_windows_models import ActionReport, ActionResult, WindowsProblem


# One action on the windows the page names, each by the identifier the list gave it. The windows are looked up afresh, as the command does for
# `--id`, so a window that closed in the meantime is reported as gone and no other window is touched in its place. One window that refuses
# does not stop the rest.
def apply_window_action(body: object) -> ActionReport | WindowsProblem:
    fields = cast(dict[str, object], body) if isinstance(body, dict) else {}
    ids_raw = fields.get("ids")
    ids = [item for item in cast(list[object], ids_raw) if isinstance(item, str)] if isinstance(ids_raw, list) else []
    if len(ids) == 0 or len(ids) > ACTION_BATCH_LIMIT or len(ids) != len(cast(list[object], ids_raw)):
        return WindowsProblem(status=400, message=f"""`ids` must be a list of one to {ACTION_BATCH_LIMIT} window identifiers.""")
    action_raw = fields.get("action")
    match action_raw if isinstance(action_raw, str) else "":
        case "minimize" | "maximize" | "unminimize" | "focus" | "close" as action:
            pass
        case _:
            return WindowsProblem(status=400, message="`action` must be minimize, maximize, unminimize, focus or close.")
    try:
        entries = {entry.id: entry for entry in collect_open_windows()}
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        return WindowsProblem(status=502, message=str(error))
    results: list[ActionResult] = []
    for window_id in ids:
        entry = entries.get(window_id)
        if entry is None:
            results.append({"id": window_id, "status": "gone", "reason": ""})
            continue
        try:
            entry.apply_action(action)
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
            results.append({"id": window_id, "status": "failed", "reason": _plain_reason(error)})
        else:
            results.append({"id": window_id, "status": "done", "reason": ""})
    return {"results": results}


# The helper's own sentence, except where macOS answered with an Accessibility error number, which says nothing to the person reading it.
def _plain_reason(error: Exception) -> str:
    if sys.platform == "darwin":
        from stackops.scripts.python.helpers.helpers_window.window_macos_api import AccessibilityError

        if isinstance(error, AccessibilityError):
            return ACCESSIBILITY_REFUSAL
    return str(error)
