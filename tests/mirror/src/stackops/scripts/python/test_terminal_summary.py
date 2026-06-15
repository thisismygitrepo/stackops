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


def test_summary_with_named_session_prints_session_details(monkeypatch) -> None:
    observed: list[str] = []

    monkeypatch.setattr(_tmux_backend, "list_session_names", lambda: ["alpha", "beta"])
    monkeypatch.setattr(terminal_summary, "_print_tmux_summary", lambda: observed.append("aggregate"))
    monkeypatch.setattr(terminal_summary, "_print_tmux_session_details", lambda session_name: observed.append(f"details:{session_name}"))

    result = CliRunner().invoke(terminal.get_app(), ["summary", "--session", "alpha"])

    assert result.exit_code == 0
    assert observed == ["details:alpha"]


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
