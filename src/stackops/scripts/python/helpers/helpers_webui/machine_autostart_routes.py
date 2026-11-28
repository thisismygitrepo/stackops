import platform
from collections.abc import Callable
from dataclasses import asdict
from typing import cast

from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from stackops.profile.dotfiles_constants import ALL_OS_VALUES
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_actions import turn_off, turn_on
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_constants import GONE_MESSAGE
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_detail import read_startup_detail
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_linux_actions import switch_linux_entry
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_login_items import remove_login_item, restore_login_item
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_model import ProblemReason, RemovedLoginItem, StartupProblem
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_read import read_startup
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_scripts import (
    add_saved_layout,
    add_tracked_script,
    apply_remembered,
    read_remembered,
    read_saved_layouts,
    remove_startup_agent,
)
from stackops.scripts.python.helpers.helpers_webui.machine_autostart_windows import switch_windows_entry
from stackops.utils.schemas.startup.startup_constants import STARTUP_WHENS
from stackops.utils.schemas.startup.startup_types import StartupWhen

PROBLEM_STATUS: dict[ProblemReason, int] = {"unsupported": 501, "failed": 409, "unknown_entry": 404, "refused": 403}
LAUNCHD_ACTIONS: dict[str, Callable[[str], StartupProblem | None]] = {"turn-off": turn_off, "turn-on": turn_on, "remove": remove_startup_agent}
# The two actions that flip an entry's switch, with whether the entry is on afterwards.
SWITCH_ACTIONS: dict[str, bool] = {"turn-off": False, "turn-on": True}


def _refusal(problem: StartupProblem) -> JSONResponse:
    return JSONResponse({"error": problem.message}, status_code=PROBLEM_STATUS[problem.reason])


# What the Startup programs page reads and does. The list is what `utils machine autostart` lists, read through the command's own helpers,
# with more about each entry than the command prints. A system it cannot be read on answers with `unavailable` and the reason, which the
# page shows in place of the list. Turning an entry off, back on, or removing it has no command, so it is done here, and only for what
# starts for the person's own account and needs no administrator: on macOS their launch agents, the agents apps installed for every
# account (for this account only) and their login items, on Linux the units of their own service manager and the desktop files in their
# autostart folder, on Windows their Run key and their Startup folder. Removing is for macOS alone. A login item taken off the list is
# remembered until this server stops, so the page can put it back. The scripts StackOps starts are also kept in startup.yaml in the
# dotfiles, for the person's other machines: the page is told how this machine differs from that file, and can make it match.
def machine_autostart_routes() -> list[Route]:
    taken_off: dict[str, RemovedLoginItem] = {}

    def read(_request: Request) -> JSONResponse:
        picture = read_startup()
        match picture:
            case StartupProblem(reason="failed"):
                return JSONResponse({"error": picture.message}, status_code=500)
            case StartupProblem():
                return JSONResponse({"unavailable": asdict(picture)})
            case _:
                return JSONResponse(picture)

    def detail(request: Request) -> JSONResponse:
        result = read_startup_detail(request.query_params.get("id", ""))
        match result:
            case StartupProblem():
                return _refusal(result)
            case _:
                return JSONResponse(result)

    def change(action: str, identifier: str) -> StartupProblem | None:
        system = platform.system()
        if system == "Linux" and action in SWITCH_ACTIONS:
            return switch_linux_entry(identifier=identifier, on=SWITCH_ACTIONS[action])
        if system == "Windows" and action in SWITCH_ACTIONS:
            return switch_windows_entry(identifier=identifier, on=SWITCH_ACTIONS[action])
        if system != "Darwin":
            return StartupProblem(reason="refused", message="That cannot be done to this entry on this system.")
        if identifier.startswith("launchd:") and action in LAUNCHD_ACTIONS:
            return LAUNCHD_ACTIONS[action](identifier)
        if identifier.startswith("login:") and action == "remove":
            removed = remove_login_item(identifier)
            match removed:
                case StartupProblem():
                    return removed
                case _:
                    taken_off[identifier] = removed
                    return None
        if identifier.startswith("login:") and action == "put-back":
            item = taken_off.get(identifier)
            if item is None:
                return StartupProblem(reason="unknown_entry", message=GONE_MESSAGE)
            problem = restore_login_item(item)
            if problem is None:
                del taken_off[identifier]
            return problem
        return StartupProblem(reason="refused", message="That cannot be done to this entry.")

    async def act(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the entry as application/json."}, status_code=415)
        body = await request.json()
        identifier = cast(dict[str, object], body).get("id") if isinstance(body, dict) else None
        if not isinstance(identifier, str):
            return JSONResponse({"error": "Name the entry to change."}, status_code=400)
        problem = await run_in_threadpool(change, request.path_params["action"], identifier)
        return _refusal(problem) if problem is not None else Response(status_code=204)

    # One of the scripts the Scripts page lists, added to what starts on its own. `base` is the folder that list was read from, `when` is
    # at sign-in or with the computer, and `systems` are the other systems startup.yaml is to list it for.
    async def add_script(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the script as application/json."}, status_code=415)
        body = await request.json()
        fields = cast(dict[str, object], body) if isinstance(body, dict) else {}
        base, script, systems = fields.get("base"), fields.get("path"), fields.get("systems")
        if not isinstance(base, str) or not isinstance(script, str):
            return JSONResponse({"error": "Name the script to add and the folder its list was read from."}, status_code=400)
        when: StartupWhen | None = next((choice for choice in STARTUP_WHENS if choice == fields.get("when")), None)
        if when is None or not isinstance(systems, list) or any(system not in ALL_OS_VALUES for system in cast(list[object], systems)):
            return JSONResponse({"error": "Say when the script starts and which other systems it is listed for."}, status_code=400)
        problem = await run_in_threadpool(add_tracked_script, base, script, when, tuple(system for system in ALL_OS_VALUES if system in systems))
        return _refusal(problem) if problem is not None else Response(status_code=204)

    # The layouts in the layout.yaml of the dotfiles, to pick the one to launch on its own from.
    def layouts(_request: Request) -> JSONResponse:
        result = read_saved_layouts()
        match result:
            case StartupProblem():
                return _refusal(result)
            case _:
                return JSONResponse(result)

    # One of those layouts, added to what starts on its own. `when` and `systems` are as for a script.
    async def add_layout(request: Request) -> Response:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the layout as application/json."}, status_code=415)
        body = await request.json()
        fields = cast(dict[str, object], body) if isinstance(body, dict) else {}
        name, systems = fields.get("name"), fields.get("systems")
        when: StartupWhen | None = next((choice for choice in STARTUP_WHENS if choice == fields.get("when")), None)
        if not isinstance(name, str) or when is None or not isinstance(systems, list) or any(system not in ALL_OS_VALUES for system in cast(list[object], systems)):
            return JSONResponse({"error": "Name the layout, say when it starts and which other systems it is listed for."}, status_code=400)
        problem = await run_in_threadpool(add_saved_layout, name, when, tuple(system for system in ALL_OS_VALUES if system in systems))
        return _refusal(problem) if problem is not None else Response(status_code=204)

    def remembered(_request: Request) -> JSONResponse:
        result = read_remembered()
        match result:
            case StartupProblem():
                return _refusal(result)
            case _:
                return JSONResponse(result)

    # `prune` also stops the scripts of the dotfiles that start here without being listed.
    async def apply(request: Request) -> JSONResponse:
        if request.headers.get("content-type") != "application/json":
            return JSONResponse({"error": "Send the request as application/json."}, status_code=415)
        body = await request.json()
        prune = cast(dict[str, object], body).get("prune") if isinstance(body, dict) else None
        if not isinstance(prune, bool):
            return JSONResponse({"error": "Say whether what is not listed is stopped as well."}, status_code=400)
        result = await run_in_threadpool(apply_remembered, prune)
        match result:
            case StartupProblem():
                return _refusal(result)
            case _:
                return JSONResponse(result)

    return [
        Route("/api/machine/autostart", read),
        Route("/api/machine/autostart/detail", detail),
        Route("/api/machine/autostart/scripts", add_script, methods=["POST"]),
        Route("/api/machine/autostart/layouts", layouts),
        Route("/api/machine/autostart/layouts", add_layout, methods=["POST"]),
        Route("/api/machine/autostart/remembered", remembered),
        Route("/api/machine/autostart/apply", apply, methods=["POST"]),
        Route("/api/machine/autostart/{action}", act, methods=["POST"]),
    ]
