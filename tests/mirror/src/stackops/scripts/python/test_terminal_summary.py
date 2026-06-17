from typer.testing import CliRunner

from stackops.scripts.python import terminal, terminal_summary
from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend


def test_summary_without_session_prints_aggregate_table(monkeypatch) -> None:
    observed: list[str] = []

    monkeypatch.setattr(terminal_summary, "_print_tmux_summary", lambda: observed.append("aggregate"))
    monkeypatch.setattr(terminal_summary, "_print_tmux_session_details", lambda session_name: observed.append(f"details:{session_name}"))

    result = CliRunner().invoke(terminal.get_app(), ["summary"])

    assert result.exit_code == 0
    assert observed == ["aggregate"]


def test_summary_with_herdr_backend_prints_aggregate_table(monkeypatch) -> None:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    monkeypatch.setattr(_herdr_backend, "list_workspace_entries", lambda: [{"workspace_id": "w1", "label": "alpha", "focused": True}])
    monkeypatch.setattr(_herdr_backend, "list_workspace_tab_entries", lambda workspace_id: [{"tab_id": f"{workspace_id}:t1", "label": "one", "agent_status": "idle", "focused": True}])
    monkeypatch.setattr(_herdr_backend, "list_workspace_pane_entries", lambda workspace_id: [{"pane_id": f"{workspace_id}:p1", "tab_id": f"{workspace_id}:t1", "agent": "codex", "agent_status": "idle", "cwd": "/tmp", "focused": True}])

    result = CliRunner().invoke(terminal.get_app(), ["summary", "--backend", "herdr"])

    assert result.exit_code == 0
    assert "Herdr workspaces" in result.output
    assert "alpha" in result.output
    assert "w1" in result.output


def test_summary_with_named_session_prints_session_details(monkeypatch) -> None:
    observed: list[str] = []

    monkeypatch.setattr(_tmux_backend, "list_session_names", lambda: ["alpha", "beta"])
    monkeypatch.setattr(terminal_summary, "_print_tmux_summary", lambda: observed.append("aggregate"))
    monkeypatch.setattr(terminal_summary, "_print_tmux_session_details", lambda session_name: observed.append(f"details:{session_name}"))

    result = CliRunner().invoke(terminal.get_app(), ["summary", "--session", "alpha"])

    assert result.exit_code == 0
    assert observed == ["details:alpha"]


def test_summary_with_named_herdr_workspace_prints_workspace_details(monkeypatch) -> None:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    monkeypatch.setattr(_herdr_backend, "list_workspace_entries", lambda: [{"workspace_id": "w1", "label": "alpha", "focused": True}])
    monkeypatch.setattr(_herdr_backend, "list_workspace_tab_entries", lambda workspace_id: [{"tab_id": f"{workspace_id}:t1", "label": "one", "agent_status": "idle", "focused": True}])
    monkeypatch.setattr(_herdr_backend, "list_workspace_pane_entries", lambda workspace_id: [{"pane_id": f"{workspace_id}:p1", "tab_id": f"{workspace_id}:t1", "agent": "codex", "agent_status": "idle", "cwd": "/tmp", "focused": True}])

    result = CliRunner().invoke(terminal.get_app(), ["summary", "--backend", "h", "--session", "alpha"])

    assert result.exit_code == 0
    assert "Workspace: alpha" in result.output
    assert "Herdr tabs" in result.output
    assert "Herdr panes" in result.output
    assert "one" in result.output


def test_summary_choose_session_prints_session_details(monkeypatch) -> None:
    observed: list[str] = []

    monkeypatch.setattr(_tmux_backend, "choose_existing_session_name", lambda msg: ("session_name", "beta"))
    monkeypatch.setattr(terminal_summary, "_print_tmux_summary", lambda: observed.append("aggregate"))
    monkeypatch.setattr(terminal_summary, "_print_tmux_session_details", lambda session_name: observed.append(f"details:{session_name}"))

    result = CliRunner().invoke(terminal.get_app(), ["summary", "--choose-session"])

    assert result.exit_code == 0
    assert observed == ["details:beta"]


def test_summary_rejects_session_and_choose_session_together(monkeypatch) -> None:
    observed: list[str] = []

    monkeypatch.setattr(terminal_summary, "_print_tmux_summary", lambda: observed.append("aggregate"))
    monkeypatch.setattr(terminal_summary, "_print_tmux_session_details", lambda session_name: observed.append(f"details:{session_name}"))

    result = CliRunner().invoke(terminal.get_app(), ["summary", "--session", "alpha", "--choose-session"])

    assert result.exit_code == 1
    assert "--session cannot be used together with --choose-session" in result.output
    assert observed == []


def test_summary_named_session_must_exist(monkeypatch) -> None:
    observed: list[str] = []

    monkeypatch.setattr(_tmux_backend, "list_session_names", lambda: ["alpha"])
    monkeypatch.setattr(terminal_summary, "_print_tmux_summary", lambda: observed.append("aggregate"))
    monkeypatch.setattr(terminal_summary, "_print_tmux_session_details", lambda session_name: observed.append(f"details:{session_name}"))

    result = CliRunner().invoke(terminal.get_app(), ["summary", "--session", "beta"])

    assert result.exit_code == 1
    assert "tmux session 'beta' not found" in result.output
    assert observed == []


def test_summary_named_herdr_workspace_must_exist(monkeypatch) -> None:
    from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend

    observed: list[str] = []

    monkeypatch.setattr(_herdr_backend, "list_workspace_entries", lambda: [{"workspace_id": "w1", "label": "alpha"}])
    monkeypatch.setattr(terminal_summary, "_print_herdr_summary", lambda: observed.append("herdr-aggregate"))
    monkeypatch.setattr(terminal_summary, "_print_herdr_workspace_details", lambda workspace_name: observed.append(f"herdr-details:{workspace_name}"))

    result = CliRunner().invoke(terminal.get_app(), ["summary", "--backend", "herdr", "--session", "beta"])

    assert result.exit_code == 1
    assert "Herdr workspace 'beta' not found" in result.output
    assert observed == []
