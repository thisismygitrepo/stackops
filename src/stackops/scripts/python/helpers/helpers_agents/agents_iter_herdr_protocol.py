from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrAgent,
    HerdrPane,
    HerdrSnapshot,
    HerdrStatus,
    HerdrTab,
    HerdrWorkspace,
    PaneId,
    TabId,
    TerminalId,
    WorkspaceId,
)


type JsonObject = dict[str, object]


class HerdrProtocolError(RuntimeError):
    pass


def parse_snapshot_response(*, payload: JsonObject) -> HerdrSnapshot:
    result = _response_result(payload=payload, expected_id="cli:api:snapshot", expected_type="session_snapshot")
    snapshot = _required_object(mapping=result, key="snapshot")

    _optional_identifier(mapping=snapshot, key="focused_workspace_id")
    _optional_identifier(mapping=snapshot, key="focused_tab_id")
    _optional_identifier(mapping=snapshot, key="focused_pane_id")
    _required_object_array(mapping=snapshot, key="layouts")

    workspaces = tuple(_parse_workspace(value=entry) for entry in _required_object_array(mapping=snapshot, key="workspaces"))
    tabs = tuple(_parse_tab(value=entry) for entry in _required_object_array(mapping=snapshot, key="tabs"))
    panes = tuple(_parse_pane(value=entry) for entry in _required_object_array(mapping=snapshot, key="panes"))
    agents = tuple(_parse_agent(value=entry) for entry in _required_object_array(mapping=snapshot, key="agents"))
    _reject_duplicate_ids(identifiers=tuple(item.workspace_id for item in workspaces), entity="workspace_id")
    _reject_duplicate_ids(identifiers=tuple(item.tab_id for item in tabs), entity="tab_id")
    _reject_duplicate_ids(identifiers=tuple(item.pane_id for item in panes), entity="pane_id")
    _reject_duplicate_ids(identifiers=tuple(item.pane_id for item in agents), entity="agent pane_id")
    return HerdrSnapshot(workspaces=workspaces, tabs=tabs, panes=panes, agents=agents)


def parse_ok_response(*, payload: JsonObject, expected_id: str) -> None:
    _response_result(payload=payload, expected_id=expected_id, expected_type="ok")


def parse_error_response(*, payload: JsonObject, expected_id: str) -> tuple[str, str]:
    response_id = _required_string(mapping=payload, key="id")
    if response_id != expected_id:
        raise HerdrProtocolError(f"Herdr returned response id {response_id!r}; expected {expected_id!r}.")
    error = _required_object(mapping=payload, key="error")
    return _required_identifier(mapping=error, key="code"), _required_string(mapping=error, key="message")


def _response_result(*, payload: JsonObject, expected_id: str, expected_type: str) -> JsonObject:
    response_id = _required_string(mapping=payload, key="id")
    if response_id != expected_id:
        raise HerdrProtocolError(f"Herdr returned response id {response_id!r}; expected {expected_id!r}.")
    result = _required_object(mapping=payload, key="result")
    response_type = _required_string(mapping=result, key="type")
    if response_type != expected_type:
        raise HerdrProtocolError(f"Herdr returned response type {response_type!r}; expected {expected_type!r}.")
    return result


def _parse_workspace(*, value: JsonObject) -> HerdrWorkspace:
    return HerdrWorkspace(
        workspace_id=WorkspaceId(_required_identifier(mapping=value, key="workspace_id")),
        label=_required_string(mapping=value, key="label"),
        number=_required_int(mapping=value, key="number", minimum=0),
        active_tab_id=TabId(_required_identifier(mapping=value, key="active_tab_id")),
        agent_status=_required_status(mapping=value, key="agent_status"),
        focused=_required_bool(mapping=value, key="focused"),
        pane_count=_required_int(mapping=value, key="pane_count", minimum=0),
        tab_count=_required_int(mapping=value, key="tab_count", minimum=0),
    )


def _parse_tab(*, value: JsonObject) -> HerdrTab:
    return HerdrTab(
        tab_id=TabId(_required_identifier(mapping=value, key="tab_id")),
        workspace_id=WorkspaceId(_required_identifier(mapping=value, key="workspace_id")),
        label=_required_string(mapping=value, key="label"),
        number=_required_int(mapping=value, key="number", minimum=0),
        agent_status=_required_status(mapping=value, key="agent_status"),
        focused=_required_bool(mapping=value, key="focused"),
        pane_count=_required_int(mapping=value, key="pane_count", minimum=0),
    )


def _parse_pane(*, value: JsonObject) -> HerdrPane:
    _focused = _required_bool(mapping=value, key="focused")
    return HerdrPane(
        pane_id=PaneId(_required_identifier(mapping=value, key="pane_id")),
        terminal_id=TerminalId(_required_identifier(mapping=value, key="terminal_id")),
        workspace_id=WorkspaceId(_required_identifier(mapping=value, key="workspace_id")),
        tab_id=TabId(_required_identifier(mapping=value, key="tab_id")),
        agent_status=_required_status(mapping=value, key="agent_status"),
        revision=_required_int(mapping=value, key="revision", minimum=0),
    )


def _parse_agent(*, value: JsonObject) -> HerdrAgent:
    return HerdrAgent(
        terminal_id=TerminalId(_required_identifier(mapping=value, key="terminal_id")),
        agent=_optional_string(mapping=value, key="agent"),
        agent_status=_required_status(mapping=value, key="agent_status"),
        workspace_id=WorkspaceId(_required_identifier(mapping=value, key="workspace_id")),
        tab_id=TabId(_required_identifier(mapping=value, key="tab_id")),
        pane_id=PaneId(_required_identifier(mapping=value, key="pane_id")),
        cwd=_optional_string(mapping=value, key="cwd"),
        foreground_cwd=_optional_string(mapping=value, key="foreground_cwd"),
        focused=_required_bool(mapping=value, key="focused"),
        name=_optional_string(mapping=value, key="name"),
        display_agent=_optional_string(mapping=value, key="display_agent"),
        revision=_required_int(mapping=value, key="revision", minimum=0),
    )


def _required_object(*, mapping: JsonObject, key: str) -> JsonObject:
    value = mapping.get(key)
    if not isinstance(value, dict):
        raise HerdrProtocolError(f"Herdr JSON response did not include an object {key}.")
    return cast(JsonObject, value)


def _required_object_array(*, mapping: JsonObject, key: str) -> tuple[JsonObject, ...]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise HerdrProtocolError(f"Herdr JSON response did not include an array {key}.")
    entries: list[JsonObject] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise HerdrProtocolError(f"Herdr JSON response {key}[{index}] was not an object.")
        entries.append(cast(JsonObject, entry))
    return tuple(entries)


def _required_identifier(*, mapping: JsonObject, key: str) -> str:
    value = _required_string(mapping=mapping, key=key)
    if value == "":
        raise HerdrProtocolError(f"Herdr JSON response included an empty {key}.")
    return value


def _required_string(*, mapping: JsonObject, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str):
        raise HerdrProtocolError(f"Herdr JSON response did not include a string {key}.")
    return value


def _optional_string(*, mapping: JsonObject, key: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise HerdrProtocolError(f"Herdr JSON response included an invalid optional {key}.")
    return value


def _optional_identifier(*, mapping: JsonObject, key: str) -> str | None:
    value = _optional_string(mapping=mapping, key=key)
    if value == "":
        raise HerdrProtocolError(f"Herdr JSON response included an empty optional {key}.")
    return value


def _required_int(*, mapping: JsonObject, key: str, minimum: int) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise HerdrProtocolError(f"Herdr JSON response did not include a usable {key}.")
    return value


def _required_bool(*, mapping: JsonObject, key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise HerdrProtocolError(f"Herdr JSON response did not include a boolean {key}.")
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
