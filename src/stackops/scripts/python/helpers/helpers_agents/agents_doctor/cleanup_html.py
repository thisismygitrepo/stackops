import json
from datetime import datetime
from pathlib import Path
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_interactive import CleanupSelection
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupEdit, CleanupPlan, CleanupRemoval
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_output import cleanup_inspection_notes
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_scope import CleanupScope
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_sizes import measure_tree
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.constants import CLEANUP_ORIGIN_LABELS
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookInventory
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorResourceState
from stackops.utils.html_report import show_html_report


class CleanupHtmlEntry(TypedDict):
    agent: str
    scope: Literal["workspace", "user", "admin", "system"]
    name: str
    event: str
    command: str
    state: DoctorResourceState
    action: Literal["delete", "disable", "read-only"]
    path: str


class CleanupHtmlChange(TypedDict):
    action: Literal["delete", "edit"]
    bytes: int
    files: int | None
    path: str


class CleanupHtmlSelection(TypedDict):
    agent: str
    directory: str
    scope: CleanupScope
    resource: str
    match: str | None
    recursive: bool


class CleanupHtmlPayload(TypedDict):
    generated_at: str
    project_root: str
    home_directory: str
    selection: CleanupHtmlSelection
    entries: list[CleanupHtmlEntry]
    changes: list[CleanupHtmlChange]
    blockers: list[str]
    notes: list[str]


def show_cleanup_html_report(
    *, plan: CleanupPlan, inventory: HookInventory, context: DoctorContext, selection: CleanupSelection
) -> Path:
    changes: list[CleanupHtmlChange] = []
    for change in sorted(plan.changes, key=lambda item: str(item.path)):
        match change:
            case CleanupRemoval():
                files, total_bytes = measure_tree(path=change.path)
                changes.append({"action": "delete", "bytes": total_bytes, "files": files, "path": str(change.path)})
            case CleanupEdit():
                changes.append({"action": "edit", "bytes": len(change.original), "files": None, "path": str(change.path)})
    payload: CleanupHtmlPayload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "project_root": str(context.project_root),
        "home_directory": str(context.home_directory),
        "selection": {
            "agent": selection.agent,
            "directory": selection.directory,
            "scope": selection.scope,
            "resource": selection.resource,
            "match": selection.match,
            "recursive": selection.recursive,
        },
        "entries": [
            {
                "agent": entry.agent,
                "scope": CLEANUP_ORIGIN_LABELS[entry.origin],
                "name": entry.name,
                "event": entry.event,
                "command": entry.command,
                "state": entry.state,
                "action": "read-only" if entry.removal is None or entry.origin in ("admin", "system") else entry.removal.action,
                "path": str(entry.path),
            }
            for entry in plan.entries
        ],
        "changes": changes,
        "blockers": list(plan.blockers),
        "notes": list(cleanup_inspection_notes(plan=plan, inventory=inventory, context=context, selection=selection)),
    }
    asset_directory = Path(__file__).with_name("html_assets")
    return show_html_report(
        title="Agent reset preview",
        payload_json=json.dumps(payload, ensure_ascii=False),
        style_path=asset_directory / "reset.css",
        script_paths=(asset_directory / "reset_data.js", asset_directory / "reset_app.js"),
        file_stem="agents_reset_preview",
    )
