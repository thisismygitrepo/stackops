import pytest
from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.scripts.python.helpers.helpers_sessions import sessions_trace


type TraceCall = tuple[
    sessions_trace.TraceBackend,
    list[str],
    sessions_trace.TraceUntil,
    float,
    int | None,
    bool,
]


def _install_trace_recorder(monkeypatch: pytest.MonkeyPatch) -> list[TraceCall]:
    observed: list[TraceCall] = []

    def fake_trace_sessions_for_backend(
        *,
        backend: sessions_trace.TraceBackend,
        session_names: list[str],
        until: sessions_trace.TraceUntil,
        every_seconds: float,
        exit_code: int | None,
        kill: bool,
    ) -> None:
        observed.append((backend, session_names, until, every_seconds, exit_code, kill))

    monkeypatch.setattr(sessions_trace, "trace_sessions_for_backend", fake_trace_sessions_for_backend)
    return observed


def test_trace_forwards_herdr_backend_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = _install_trace_recorder(monkeypatch=monkeypatch)

    result = CliRunner().invoke(
        terminal.get_app(),
        ["trace", "build", "--backend", "h", "--until", "all-exited", "--every", "1.5"],
    )

    assert result.exit_code == 0
    assert observed == [("herdr", ["build"], "all-exited", 1.5, None, False)]


def test_trace_forwards_aoe_backend_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = _install_trace_recorder(monkeypatch=monkeypatch)

    result = CliRunner().invoke(
        terminal.get_app(),
        ["trace", "build", "--backend", "a", "--until", "all-exited", "--every", "1.5"],
    )

    assert result.exit_code == 0
    assert observed == [("aoe", ["build"], "all-exited", 1.5, None, False)]


def test_trace_forwards_comma_separated_session_names(monkeypatch: pytest.MonkeyPatch) -> None:
    observed = _install_trace_recorder(monkeypatch=monkeypatch)

    result = CliRunner().invoke(terminal.get_app(), ["trace", "build, test,build"])

    assert result.exit_code == 0
    assert observed == [("tmux", ["build", "test"], "idle-shell", 10.0, None, False)]


def test_trace_expands_star_and_question_mark_patterns_without_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend

    observed = _install_trace_recorder(monkeypatch=monkeypatch)

    def fake_list_session_names() -> list[str]:
        return ["build-a", "build-b", "qa-1", "qa-12", "other"]

    monkeypatch.setattr(_tmux_backend, "list_session_names", fake_list_session_names)

    result = CliRunner().invoke(terminal.get_app(), ["trace", "build-*,build-?,qa-?"])

    assert result.exit_code == 0
    assert observed == [("tmux", ["build-a", "build-b", "qa-1"], "idle-shell", 10.0, None, False)]


def test_trace_rejects_pattern_matching_no_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend

    observed = _install_trace_recorder(monkeypatch=monkeypatch)

    def fake_list_session_names() -> list[str]:
        return ["build", "test"]

    monkeypatch.setattr(_tmux_backend, "list_session_names", fake_list_session_names)

    result = CliRunner().invoke(terminal.get_app(), ["trace", "missing-*"])

    assert result.exit_code == 1
    assert "Session selector 'missing-*' matched no tmux sessions." in result.output
    assert observed == []


def test_trace_interactive_tmux_uses_multi_select_picker(monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend

    observed = _install_trace_recorder(monkeypatch=monkeypatch)
    picker_calls: list[tuple[str, dict[str, str], bool]] = []

    def fake_list_session_names() -> list[str]:
        return ["build", "test"]

    def fake_build_preview(session_name: str) -> str:
        return f"preview: {session_name}"

    def fake_interactive_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool,
    ) -> list[str]:
        picker_calls.append((msg, options_to_preview_mapping, multi))
        return ["build", "test"]

    monkeypatch.setattr(_tmux_backend, "list_session_names", fake_list_session_names)
    monkeypatch.setattr(_tmux_backend, "_build_preview", fake_build_preview)
    monkeypatch.setattr(_tmux_backend, "interactive_choose_with_preview", fake_interactive_choose_with_preview)

    result = CliRunner().invoke(terminal.get_app(), ["trace", "--interactive"])

    assert result.exit_code == 0
    assert picker_calls == [
        (
            "Choose tmux sessions to trace:",
            {"build": "preview: build", "test": "preview: test"},
            True,
        )
    ]
    assert observed == [("tmux", ["build", "test"], "idle-shell", 10.0, None, False)]


def test_trace_interactive_herdr_uses_workspace_picker(monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.scripts.python.helpers.helpers_sessions import session_trace_herdr

    observed = _install_trace_recorder(monkeypatch=monkeypatch)

    def fake_choose_existing_workspace_names(msg: str) -> session_trace_herdr.WorkspaceChoice:
        assert msg == "Choose Herdr workspaces to trace:"
        return ("session_names", ["workspace-a", "workspace-b"])

    monkeypatch.setattr(session_trace_herdr, "choose_existing_workspace_names", fake_choose_existing_workspace_names)

    result = CliRunner().invoke(
        terminal.get_app(),
        ["trace", "--backend", "herdr", "--interactive"],
    )

    assert result.exit_code == 0
    assert observed == [("herdr", ["workspace-a", "workspace-b"], "idle-shell", 10.0, None, False)]


def test_trace_interactive_aoe_uses_session_picker(monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.scripts.python.helpers.helpers_sessions import session_trace_aoe

    observed = _install_trace_recorder(monkeypatch=monkeypatch)

    def fake_choose_existing_session_names(msg: str) -> session_trace_aoe.SessionChoice:
        assert msg == "Choose AoE sessions to trace:"
        return ("session_names", ["session-a", "session-b"])

    monkeypatch.setattr(session_trace_aoe, "choose_existing_session_names", fake_choose_existing_session_names)

    result = CliRunner().invoke(
        terminal.get_app(),
        ["trace", "--backend", "aoe", "--interactive"],
    )

    assert result.exit_code == 0
    assert observed == [("aoe", ["session-a", "session-b"], "idle-shell", 10.0, None, False)]


@pytest.mark.parametrize("kill_flag", ["--kill", "-k"])
def test_trace_forwards_kill_option(
    monkeypatch: pytest.MonkeyPatch,
    kill_flag: str,
) -> None:
    observed = _install_trace_recorder(monkeypatch=monkeypatch)

    result = CliRunner().invoke(terminal.get_app(), ["trace", "build", kill_flag])

    assert result.exit_code == 0
    assert observed == [("tmux", ["build"], "idle-shell", 10.0, None, True)]
