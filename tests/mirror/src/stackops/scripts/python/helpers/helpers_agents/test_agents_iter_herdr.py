import json
import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_herdr
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import PaneId, TabId, WorkspaceId


def _workspace_entry() -> dict[str, object]:
    return {
        "workspace_id": "w1",
        "label": "iter-alpha",
        "number": 1,
        "active_tab_id": "w1:t1",
        "agent_status": "working",
        "focused": True,
        "pane_count": 1,
        "tab_count": 1,
    }


def _tab_entry() -> dict[str, object]:
    return {
        "tab_id": "w1:t1",
        "workspace_id": "w1",
        "label": "iter-alpha-001",
        "number": 1,
        "agent_status": "idle",
        "focused": True,
        "pane_count": 1,
    }


def _pane_entry() -> dict[str, object]:
    return {
        "pane_id": "w1:p1",
        "workspace_id": "w1",
        "tab_id": "w1:t1",
        "agent_status": "blocked",
        "agent": "codex",
        "label": "iter-alpha-001",
    }


def _agent_entry() -> dict[str, object]:
    return {
        "agent": "codex",
        "agent_status": "unknown",
        "workspace_id": "w1",
        "tab_id": "w1:t1",
        "pane_id": "w1:p1",
        "cwd": "/repo",
        "foreground_cwd": "/repo/src",
        "focused": True,
        "name": "iter-alpha-001",
    }


def _json_result(*, key: str, entries: list[object]) -> str:
    return json.dumps({"result": {key: entries}})


def test_capture_herdr_snapshot_parses_all_entities_and_uses_bounded_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = {
        ("herdr", "workspace", "list"): _json_result(key="workspaces", entries=[_workspace_entry()]),
        ("herdr", "tab", "list"): _json_result(key="tabs", entries=[_tab_entry()]),
        ("herdr", "pane", "list"): _json_result(key="panes", entries=[_pane_entry()]),
        ("herdr", "agent", "list"): _json_result(key="agents", entries=[_agent_entry()]),
    }
    observed_commands: list[tuple[str, ...]] = []

    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        check: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert check is False
        assert text is True
        assert timeout == agents_iter_herdr.HERDR_COMMAND_TIMEOUT_SECONDS
        observed_commands.append(command)
        return subprocess.CompletedProcess(command, 0, responses[command], "")

    monkeypatch.setattr(agents_iter_herdr.subprocess, "run", fake_run)

    snapshot = agents_iter_herdr.capture_herdr_snapshot()

    assert observed_commands == [
        ("herdr", "workspace", "list"),
        ("herdr", "tab", "list"),
        ("herdr", "pane", "list"),
        ("herdr", "agent", "list"),
    ]
    assert snapshot.workspaces[0].workspace_id == WorkspaceId("w1")
    assert snapshot.workspaces[0].agent_status == "working"
    assert snapshot.tabs[0].tab_id == TabId("w1:t1")
    assert snapshot.tabs[0].agent_status == "idle"
    assert snapshot.panes[0].pane_id == PaneId("w1:p1")
    assert snapshot.panes[0].agent_status == "blocked"
    assert snapshot.agents[0].name == "iter-alpha-001"
    assert snapshot.agents[0].agent_status == "unknown"


@pytest.mark.parametrize("status", ["blocked", "done", "idle", "unknown", "working"])
def test_list_tabs_accepts_every_known_status(monkeypatch: pytest.MonkeyPatch, status: str) -> None:
    entry = _tab_entry()
    entry["agent_status"] = status
    monkeypatch.setattr(
        agents_iter_herdr,
        "_run_herdr",
        lambda *, command: _json_result(key="tabs", entries=[entry]),
    )

    tabs = agents_iter_herdr.list_tabs()

    assert tabs[0].agent_status == status


def test_list_tabs_rejects_unknown_status(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = _tab_entry()
    entry["agent_status"] = "sleeping"
    monkeypatch.setattr(
        agents_iter_herdr,
        "_run_herdr",
        lambda *, command: _json_result(key="tabs", entries=[entry]),
    )

    with pytest.raises(agents_iter_herdr.HerdrProtocolError, match="unknown agent_status 'sleeping'"):
        agents_iter_herdr.list_tabs()


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("number", True),
        ("number", 0),
        ("label", ""),
        ("label", "   "),
        ("focused", 1),
        ("pane_count", -1),
    ],
)
def test_list_workspaces_rejects_malformed_required_fields(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid_value: object,
) -> None:
    entry = _workspace_entry()
    entry[field] = invalid_value
    monkeypatch.setattr(
        agents_iter_herdr,
        "_run_herdr",
        lambda *, command: _json_result(key="workspaces", entries=[entry]),
    )

    with pytest.raises(agents_iter_herdr.HerdrProtocolError):
        agents_iter_herdr.list_workspaces()


def test_list_agents_rejects_empty_optional_string(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = _agent_entry()
    entry["name"] = ""
    monkeypatch.setattr(
        agents_iter_herdr,
        "_run_herdr",
        lambda *, command: _json_result(key="agents", entries=[entry]),
    )

    with pytest.raises(agents_iter_herdr.HerdrProtocolError, match="invalid optional name"):
        agents_iter_herdr.list_agents()


def test_list_tabs_rejects_duplicate_stable_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    duplicate = _tab_entry()
    duplicate["label"] = "iter-alpha-duplicate"
    monkeypatch.setattr(
        agents_iter_herdr,
        "_run_herdr",
        lambda *, command: _json_result(key="tabs", entries=[_tab_entry(), duplicate]),
    )

    with pytest.raises(agents_iter_herdr.HerdrProtocolError, match="duplicate tab_id 'w1:t1'"):
        agents_iter_herdr.list_tabs()


def test_list_agents_rejects_duplicate_agent_pane_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    duplicate = _agent_entry()
    duplicate["name"] = "iter-alpha-002"
    monkeypatch.setattr(
        agents_iter_herdr,
        "_run_herdr",
        lambda *, command: _json_result(key="agents", entries=[_agent_entry(), duplicate]),
    )

    with pytest.raises(agents_iter_herdr.HerdrProtocolError, match="duplicate agent pane_id 'w1:p1'"):
        agents_iter_herdr.list_agents()


@pytest.mark.parametrize(
    "response",
    [
        "",
        "not json",
        "[]",
        "{}",
        '{"result": {"tabs": {}}}',
        '{"result": {"tabs": [false]}}',
    ],
)
def test_list_tabs_rejects_malformed_protocol_responses(
    monkeypatch: pytest.MonkeyPatch,
    response: str,
) -> None:
    monkeypatch.setattr(agents_iter_herdr, "_run_herdr", lambda *, command: response)

    with pytest.raises(agents_iter_herdr.HerdrProtocolError):
        agents_iter_herdr.list_tabs()


def test_herdr_timeout_is_a_typed_command_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        check: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=command, timeout=timeout)

    monkeypatch.setattr(agents_iter_herdr.subprocess, "run", fake_run)

    with pytest.raises(agents_iter_herdr.HerdrCommandError, match="timed out after 15 second"):
        agents_iter_herdr.list_tabs()


def test_herdr_nonzero_exit_is_a_typed_command_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        check: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 9, "", "socket unavailable")

    monkeypatch.setattr(agents_iter_herdr.subprocess, "run", fake_run)

    with pytest.raises(agents_iter_herdr.HerdrCommandError, match="socket unavailable"):
        agents_iter_herdr.list_workspaces()


def test_missing_herdr_is_a_typed_command_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: tuple[str, ...],
        *,
        capture_output: bool,
        check: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(agents_iter_herdr.subprocess, "run", fake_run)

    with pytest.raises(agents_iter_herdr.HerdrCommandError, match="not found in PATH"):
        agents_iter_herdr.list_panes()


def test_close_commands_use_stable_typed_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_commands: list[tuple[str, ...]] = []

    def fake_run_herdr(*, command: tuple[str, ...]) -> str:
        observed_commands.append(command)
        return ""

    monkeypatch.setattr(agents_iter_herdr, "_run_herdr", fake_run_herdr)

    agents_iter_herdr.close_tab(tab_id=TabId("w1:t1"))
    agents_iter_herdr.close_workspace(workspace_id=WorkspaceId("w1"))

    assert observed_commands == [
        ("herdr", "tab", "close", "w1:t1"),
        ("herdr", "workspace", "close", "w1"),
    ]


def test_close_commands_reject_empty_ids() -> None:
    with pytest.raises(ValueError, match="tab id must not be empty"):
        agents_iter_herdr.close_tab(tab_id=TabId(""))
    with pytest.raises(ValueError, match="workspace id must not be empty"):
        agents_iter_herdr.close_workspace(workspace_id=WorkspaceId(" "))
