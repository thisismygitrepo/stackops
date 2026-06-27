import json
import shlex
from typing import TypeAlias, cast

from stackops.scripts.python.helpers.helpers_sessions._attach_common import (
    natural_sort_key,
    run_command,
)

JsonObject: TypeAlias = dict[str, object]


def run_herdr_json(args: list[str]) -> JsonObject:
    try:
        result = run_command(args)
    except FileNotFoundError as exc:
        raise ValueError("Herdr backend requested, but `herdr` was not found in PATH.") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise ValueError(f"Herdr command failed ({shlex.join(args)}): {detail}")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Herdr command returned invalid JSON ({shlex.join(args)}).") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"Herdr command returned non-object JSON ({shlex.join(args)}).")
    return cast(JsonObject, parsed)


def dict_entries(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [cast(JsonObject, item) for item in value if isinstance(item, dict)]


def result_entries(payload: JsonObject, key: str) -> list[JsonObject]:
    result = payload.get("result")
    if not isinstance(result, dict):
        return []
    return dict_entries(result.get(key))


def entry_text(entry: JsonObject, key: str) -> str | None:
    value = entry.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def entry_int(entry: JsonObject, key: str) -> int | None:
    value = entry.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped_value = value.strip()
        if stripped_value.startswith("-") and stripped_value[1:].isdigit():
            return int(stripped_value)
        if stripped_value.isdigit():
            return int(stripped_value)
    return None


def workspace_id(workspace: JsonObject) -> str | None:
    return entry_text(workspace, "workspace_id")


def workspace_label(workspace: JsonObject) -> str | None:
    return entry_text(workspace, "label")


def workspace_display_name(workspace: JsonObject) -> str:
    return (
        workspace_label(workspace)
        or workspace_id(workspace)
        or "workspace"
    )


def workspace_sort_key(workspace: JsonObject) -> tuple[bool, int, list[int | str]]:
    number = entry_int(workspace, "number")
    return (
        not bool(workspace.get("focused")),
        number if number is not None else 999_999,
        natural_sort_key(workspace_display_name(workspace)),
    )


def list_workspace_entries() -> list[JsonObject]:
    payload = run_herdr_json(["herdr", "workspace", "list"])
    workspaces = result_entries(payload=payload, key="workspaces")
    workspaces.sort(key=workspace_sort_key)
    return workspaces


def tab_id(tab: JsonObject) -> str | None:
    return entry_text(tab, "tab_id")


def tab_sort_key(tab: JsonObject) -> tuple[int, str]:
    number = entry_int(tab, "number")
    return (number if number is not None else 999_999, tab_id(tab) or "")


def pane_sort_key(pane: JsonObject) -> tuple[str, str]:
    return (
        entry_text(pane, "tab_id") or "",
        entry_text(pane, "pane_id") or "",
    )


def load_tab_entries(workspace_id_value: str) -> list[JsonObject]:
    payload = run_herdr_json(["herdr", "tab", "list", "--workspace", workspace_id_value])
    tabs = result_entries(payload=payload, key="tabs")
    tabs.sort(key=tab_sort_key)
    return tabs


def load_pane_entries(workspace_id_value: str) -> list[JsonObject]:
    payload = run_herdr_json(["herdr", "pane", "list", "--workspace", workspace_id_value])
    panes = result_entries(payload=payload, key="panes")
    panes.sort(key=pane_sort_key)
    return panes
