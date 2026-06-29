import json
import shlex
import subprocess
from typing import Final, cast

from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrAgent,
    HerdrPane,
    HerdrSnapshot,
    HerdrStatus,
    HerdrTab,
    HerdrWorkspace,
    PaneId,
    TabId,
    WorkspaceId,
)


type JsonObject = dict[str, object]

HERDR_COMMAND_TIMEOUT_SECONDS: Final[int] = 15


class HerdrError(RuntimeError):
    pass


class HerdrCommandError(HerdrError):
    pass


class HerdrProtocolError(HerdrError):
    pass


def capture_herdr_snapshot() -> HerdrSnapshot:
    return HerdrSnapshot(
        workspaces=list_workspaces(),
        tabs=list_tabs(),
        panes=list_panes(),
        agents=list_agents(),
    )


def list_workspaces() -> tuple[HerdrWorkspace, ...]:
    entries = _result_entries(command=("herdr", "workspace", "list"), key="workspaces")
    workspaces = tuple(_parse_workspace(value=entry) for entry in entries)
    _reject_duplicate_ids(
        identifiers=tuple(workspace.workspace_id for workspace in workspaces),
        entity="workspace_id",
    )
    return workspaces


def list_tabs() -> tuple[HerdrTab, ...]:
    entries = _result_entries(command=("herdr", "tab", "list"), key="tabs")
    tabs = tuple(_parse_tab(value=entry) for entry in entries)
    _reject_duplicate_ids(
        identifiers=tuple(tab.tab_id for tab in tabs),
        entity="tab_id",
    )
    return tabs


def list_panes() -> tuple[HerdrPane, ...]:
    entries = _result_entries(command=("herdr", "pane", "list"), key="panes")
    panes = tuple(_parse_pane(value=entry) for entry in entries)
    _reject_duplicate_ids(
        identifiers=tuple(pane.pane_id for pane in panes),
        entity="pane_id",
    )
    return panes


def list_agents() -> tuple[HerdrAgent, ...]:
    entries = _result_entries(command=("herdr", "agent", "list"), key="agents")
    agents = tuple(_parse_agent(value=entry) for entry in entries)
    _reject_duplicate_ids(
        identifiers=tuple(agent.pane_id for agent in agents),
        entity="agent pane_id",
    )
    return agents


def close_tab(*, tab_id: TabId) -> None:
    if str(tab_id).strip() == "":
        raise ValueError("Herdr tab id must not be empty.")
    _run_herdr(command=("herdr", "tab", "close", tab_id))


def close_workspace(*, workspace_id: WorkspaceId) -> None:
    if str(workspace_id).strip() == "":
        raise ValueError("Herdr workspace id must not be empty.")
    _run_herdr(command=("herdr", "workspace", "close", workspace_id))


def _run_herdr(*, command: tuple[str, ...]) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=HERDR_COMMAND_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        raise HerdrCommandError("Iter maintenance requested Herdr, but `herdr` was not found in PATH.") from error
    except subprocess.TimeoutExpired as error:
        raise HerdrCommandError(
            f"Herdr command timed out after {HERDR_COMMAND_TIMEOUT_SECONDS} second(s): {shlex.join(command)}"
        ) from error
    if result.returncode == 0:
        return result.stdout
    detail = (result.stderr or result.stdout or "unknown error").strip()
    raise HerdrCommandError(f"Herdr command failed ({shlex.join(command)}): {detail}")


def _run_herdr_json(*, command: tuple[str, ...]) -> JsonObject:
    stdout = _run_herdr(command=command).strip()
    if stdout == "":
        raise HerdrProtocolError(f"Herdr command did not return JSON: {shlex.join(command)}")
    try:
        payload = cast(object, json.loads(stdout))
    except json.JSONDecodeError as error:
        raise HerdrProtocolError(f"Herdr command returned invalid JSON: {shlex.join(command)}") from error
    if not isinstance(payload, dict):
        raise HerdrProtocolError(f"Herdr command returned non-object JSON: {shlex.join(command)}")
    return cast(JsonObject, payload)


def _result_entries(*, command: tuple[str, ...], key: str) -> tuple[JsonObject, ...]:
    payload = _run_herdr_json(command=command)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise HerdrProtocolError("Herdr JSON response did not include an object result.")
    entries = result.get(key)
    if not isinstance(entries, list):
        raise HerdrProtocolError(f"Herdr JSON response did not include result.{key}.")
    parsed_entries: list[JsonObject] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise HerdrProtocolError(f"Herdr result.{key}[{index}] was not an object.")
        parsed_entries.append(cast(JsonObject, entry))
    return tuple(parsed_entries)


def _parse_workspace(*, value: JsonObject) -> HerdrWorkspace:
    return HerdrWorkspace(
        workspace_id=WorkspaceId(_required_string(mapping=value, key="workspace_id")),
        label=_required_string(mapping=value, key="label"),
        number=_required_int(mapping=value, key="number", minimum=1),
        active_tab_id=TabId(_required_string(mapping=value, key="active_tab_id")),
        agent_status=_required_status(mapping=value, key="agent_status"),
        focused=_required_bool(mapping=value, key="focused"),
        pane_count=_required_int(mapping=value, key="pane_count", minimum=0),
        tab_count=_required_int(mapping=value, key="tab_count", minimum=0),
    )


def _parse_tab(*, value: JsonObject) -> HerdrTab:
    return HerdrTab(
        tab_id=TabId(_required_string(mapping=value, key="tab_id")),
        workspace_id=WorkspaceId(_required_string(mapping=value, key="workspace_id")),
        label=_required_string(mapping=value, key="label"),
        number=_required_int(mapping=value, key="number", minimum=1),
        agent_status=_required_status(mapping=value, key="agent_status"),
        focused=_required_bool(mapping=value, key="focused"),
        pane_count=_required_int(mapping=value, key="pane_count", minimum=0),
    )


def _parse_agent(*, value: JsonObject) -> HerdrAgent:
    return HerdrAgent(
        agent=_required_string(mapping=value, key="agent"),
        agent_status=_required_status(mapping=value, key="agent_status"),
        workspace_id=WorkspaceId(_required_string(mapping=value, key="workspace_id")),
        tab_id=TabId(_required_string(mapping=value, key="tab_id")),
        pane_id=PaneId(_required_string(mapping=value, key="pane_id")),
        cwd=_required_string(mapping=value, key="cwd"),
        foreground_cwd=_required_string(mapping=value, key="foreground_cwd"),
        focused=_required_bool(mapping=value, key="focused"),
        name=_optional_string(mapping=value, key="name"),
    )


def _parse_pane(*, value: JsonObject) -> HerdrPane:
    return HerdrPane(
        pane_id=PaneId(_required_string(mapping=value, key="pane_id")),
        workspace_id=WorkspaceId(_required_string(mapping=value, key="workspace_id")),
        tab_id=TabId(_required_string(mapping=value, key="tab_id")),
        agent_status=_required_status(mapping=value, key="agent_status"),
        agent=_optional_string(mapping=value, key="agent"),
        label=_optional_string(mapping=value, key="label"),
    )


def _required_string(*, mapping: JsonObject, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise HerdrProtocolError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _optional_string(*, mapping: JsonObject, key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or value.strip() == "":
        raise HerdrProtocolError(f"Herdr JSON response included an invalid optional {key}.")
    return value


def _required_int(*, mapping: JsonObject, key: str, minimum: int) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise HerdrProtocolError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _required_bool(*, mapping: JsonObject, key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise HerdrProtocolError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _required_status(*, mapping: JsonObject, key: str) -> HerdrStatus:
    value = _required_string(mapping=mapping, key=key)
    match value:
        case "blocked" | "done" | "idle" | "unknown" | "working":
            return value
        case _:
            raise HerdrProtocolError(f"Herdr JSON response included unknown {key} {value!r}.")


def _reject_duplicate_ids(*, identifiers: tuple[str, ...], entity: str) -> None:
    seen: set[str] = set()
    for identifier in identifiers:
        if identifier in seen:
            raise HerdrProtocolError(f"Herdr JSON response included duplicate {entity} {identifier!r}.")
        seen.add(identifier)
