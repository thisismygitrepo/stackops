import json
import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_herdr
from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import HERDR_COMMAND_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr import HerdrApiError
from stackops.scripts.python.helpers.helpers_agents.agents_iter_herdr_protocol import HerdrProtocolError, JsonObject, parse_snapshot_response
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import TabId


def _snapshot_payload() -> JsonObject:
    return {
        "id": "cli:api:snapshot",
        "result": {
            "type": "session_snapshot",
            "snapshot": {
                "focused_workspace_id": "w1",
                "focused_tab_id": "w1:t1",
                "focused_pane_id": "w1:p1",
                "workspaces": [
                    {
                        "workspace_id": "w1",
                        "number": 0,
                        "label": "",
                        "focused": True,
                        "pane_count": 1,
                        "tab_count": 1,
                        "active_tab_id": "w1:t1",
                        "agent_status": "idle",
                    }
                ],
                "tabs": [
                    {"tab_id": "w1:t1", "workspace_id": "w1", "number": 0, "label": "", "focused": True, "pane_count": 1, "agent_status": "idle"}
                ],
                "panes": [
                    {
                        "pane_id": "w1:p1",
                        "terminal_id": "term_1",
                        "workspace_id": "w1",
                        "tab_id": "w1:t1",
                        "focused": True,
                        "agent_status": "idle",
                        "revision": 7,
                    }
                ],
                "layouts": [],
                "agents": [
                    {
                        "terminal_id": "term_1",
                        "name": "iter-alpha-001",
                        "agent": None,
                        "agent_status": "idle",
                        "workspace_id": "w1",
                        "tab_id": "w1:t1",
                        "pane_id": "w1:p1",
                        "focused": True,
                        "cwd": None,
                        "foreground_cwd": None,
                        "revision": 7,
                    }
                ],
            },
        },
    }


def test_capture_uses_one_atomic_current_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_commands: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], *, capture_output: bool, check: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        assert capture_output is True
        assert check is False
        assert text is True
        assert timeout == HERDR_COMMAND_TIMEOUT_SECONDS
        observed_commands.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps(_snapshot_payload()), "")

    monkeypatch.setattr(agents_iter_herdr.subprocess, "run", fake_run)

    snapshot = agents_iter_herdr.capture_herdr_snapshot()

    assert observed_commands == [("herdr", "api", "snapshot")]
    assert snapshot.workspaces[0].number == 0
    assert snapshot.workspaces[0].label == ""
    assert snapshot.agents[0].agent is None
    assert snapshot.agents[0].cwd is None
    assert snapshot.agents[0].foreground_cwd is None
    assert snapshot.agents[0].revision == 7


@pytest.mark.parametrize(
    ("path", "value", "message"),
    (
        (("id",), "cli:workspace:list", "response id"),
        (("result", "type"), "workspace_list", "response type"),
    ),
)
def test_snapshot_rejects_every_noncurrent_envelope(path: tuple[str, ...], value: object, message: str) -> None:
    payload = _snapshot_payload()
    target = payload
    for key in path[:-1]:
        child = target[key]
        assert isinstance(child, dict)
        target = child
    target[path[-1]] = value

    with pytest.raises(HerdrProtocolError, match=message):
        parse_snapshot_response(payload=payload)


@pytest.mark.parametrize(("entity", "field"), (("panes", "terminal_id"), ("panes", "revision"), ("agents", "terminal_id"), ("agents", "revision")))
def test_snapshot_requires_terminal_id_and_revision(entity: str, field: str) -> None:
    payload = _snapshot_payload()
    result = payload["result"]
    assert isinstance(result, dict)
    snapshot = result["snapshot"]
    assert isinstance(snapshot, dict)
    entries = snapshot[entity]
    assert isinstance(entries, list)
    entry = entries[0]
    assert isinstance(entry, dict)
    del entry[field]

    with pytest.raises(HerdrProtocolError, match=field):
        parse_snapshot_response(payload=payload)


def test_close_requires_exact_ok_response(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_commands: list[tuple[str, ...]] = []

    def fake_run(command: tuple[str, ...], *, capture_output: bool, check: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        observed_commands.append(command)
        return subprocess.CompletedProcess(command, 0, '{"id":"cli:tab:close","result":{"type":"ok"}}', "")

    monkeypatch.setattr(agents_iter_herdr.subprocess, "run", fake_run)

    agents_iter_herdr.close_tab(tab_id=TabId("w1:t1"))

    assert observed_commands == [("herdr", "tab", "close", "w1:t1")]


def test_close_exposes_current_api_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: tuple[str, ...], *, capture_output: bool, check: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        response = '{"id":"cli:tab:close","error":{"code":"tab_not_found","message":"gone"}}'
        return subprocess.CompletedProcess(command, 1, response, "")

    monkeypatch.setattr(agents_iter_herdr.subprocess, "run", fake_run)

    with pytest.raises(HerdrApiError) as error:
        agents_iter_herdr.close_tab(tab_id=TabId("w1:t1"))

    assert error.value.code == "tab_not_found"


def test_close_rejects_empty_success_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: tuple[str, ...], *, capture_output: bool, check: bool, text: bool, timeout: int) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(agents_iter_herdr.subprocess, "run", fake_run)

    with pytest.raises(HerdrProtocolError, match="did not return JSON"):
        agents_iter_herdr.close_tab(tab_id=TabId("w1:t1"))
