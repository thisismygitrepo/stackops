from typer.testing import CliRunner

from stackops.scripts.python import terminal
from stackops.scripts.python.helpers.helpers_sessions import sessions_trace


def test_trace_forwards_herdr_backend_alias(monkeypatch) -> None:
    observed: list[tuple[str, str, str, float, int | None]] = []

    def fake_trace_session_for_backend(
        *,
        backend: sessions_trace.TraceBackend,
        session_name: str,
        until: sessions_trace.TraceUntil,
        every_seconds: float,
        exit_code: int | None,
    ) -> None:
        observed.append((backend, session_name, until, every_seconds, exit_code))

    monkeypatch.setattr(sessions_trace, "trace_session_for_backend", fake_trace_session_for_backend)

    result = CliRunner().invoke(
        terminal.get_app(),
        ["trace", "build", "--backend", "h", "--until", "all-exited", "--every", "1.5"],
    )

    assert result.exit_code == 0
    assert observed == [("herdr", "build", "all-exited", 1.5, None)]


def test_trace_forwards_aoe_backend_alias(monkeypatch) -> None:
    observed: list[tuple[str, str, str, float, int | None]] = []

    def fake_trace_session_for_backend(
        *,
        backend: sessions_trace.TraceBackend,
        session_name: str,
        until: sessions_trace.TraceUntil,
        every_seconds: float,
        exit_code: int | None,
    ) -> None:
        observed.append((backend, session_name, until, every_seconds, exit_code))

    monkeypatch.setattr(sessions_trace, "trace_session_for_backend", fake_trace_session_for_backend)

    result = CliRunner().invoke(
        terminal.get_app(),
        ["trace", "build", "--backend", "a", "--until", "all-exited", "--every", "1.5"],
    )

    assert result.exit_code == 0
    assert observed == [("aoe", "build", "all-exited", 1.5, None)]


def test_trace_interactive_herdr_uses_workspace_picker(monkeypatch) -> None:
    observed: list[tuple[str, str]] = []

    def fake_trace_session_for_backend(
        *,
        backend: sessions_trace.TraceBackend,
        session_name: str,
        until: sessions_trace.TraceUntil,
        every_seconds: float,
        exit_code: int | None,
    ) -> None:
        _ = until, every_seconds, exit_code
        observed.append((backend, session_name))

    from stackops.scripts.python.helpers.helpers_sessions import session_trace_herdr

    monkeypatch.setattr(sessions_trace, "trace_session_for_backend", fake_trace_session_for_backend)
    monkeypatch.setattr(
        session_trace_herdr,
        "choose_existing_workspace_name",
        lambda msg: ("session_name", "chosen-workspace"),
    )

    result = CliRunner().invoke(
        terminal.get_app(),
        ["trace", "--backend", "herdr", "--interactive"],
    )

    assert result.exit_code == 0
    assert observed == [("herdr", "chosen-workspace")]


def test_trace_interactive_aoe_uses_session_picker(monkeypatch) -> None:
    observed: list[tuple[str, str]] = []

    def fake_trace_session_for_backend(
        *,
        backend: sessions_trace.TraceBackend,
        session_name: str,
        until: sessions_trace.TraceUntil,
        every_seconds: float,
        exit_code: int | None,
    ) -> None:
        _ = until, every_seconds, exit_code
        observed.append((backend, session_name))

    from stackops.scripts.python.helpers.helpers_sessions import session_trace_aoe

    monkeypatch.setattr(sessions_trace, "trace_session_for_backend", fake_trace_session_for_backend)
    monkeypatch.setattr(
        session_trace_aoe,
        "choose_existing_session_name",
        lambda msg: ("session_name", "chosen-session"),
    )

    result = CliRunner().invoke(
        terminal.get_app(),
        ["trace", "--backend", "aoe", "--interactive"],
    )

    assert result.exit_code == 0
    assert observed == [("aoe", "chosen-session")]
