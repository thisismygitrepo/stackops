import pytest

from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend


def _session(name: str, running: bool) -> _herdr_backend.JsonObject:
    session: _herdr_backend.JsonObject = {"name": name, "running": running}
    return session


def test_attach_single_running_session_still_shows_action_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_options: list[list[str]] = []

    def fake_session_entries() -> list[_herdr_backend.JsonObject]:
        return [
            _session(name="running", running=True),
            _session(name="stopped", running=False),
        ]

    def fake_interactive_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool = False,
    ) -> list[str] | str | None:
        assert msg == "Choose a Herdr session to attach to:"
        assert multi is False
        observed_options.append(list(options_to_preview_mapping))
        return "running"

    monkeypatch.setattr(_herdr_backend, "_session_entries", fake_session_entries)
    monkeypatch.setattr(_herdr_backend, "interactive_choose_with_preview", fake_interactive_choose_with_preview)

    action, payload = _herdr_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
    )

    assert action == "handoff_script"
    assert payload == "herdr session attach running"
    assert observed_options == [["running", "NEW SESSION", "KILL ALL SESSIONS & START NEW"]]


def test_attach_starts_new_session_when_only_stopped_records_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_session_entries() -> list[_herdr_backend.JsonObject]:
        return [_session(name="stopped", running=False)]

    monkeypatch.setattr(_herdr_backend, "_session_entries", fake_session_entries)

    action, payload = _herdr_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
    )

    assert action == "handoff_script"
    assert payload == "herdr"


def test_attach_kill_all_and_new_menu_action_stops_running_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_session_entries() -> list[_herdr_backend.JsonObject]:
        return [
            _session(name="alpha", running=True),
            _session(name="beta", running=True),
            _session(name="stopped", running=False),
        ]

    def fake_interactive_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool = False,
    ) -> list[str] | str | None:
        _ = msg, multi
        assert list(options_to_preview_mapping) == [
            "alpha",
            "beta",
            "NEW SESSION",
            "KILL ALL SESSIONS & START NEW",
        ]
        return "KILL ALL SESSIONS & START NEW"

    monkeypatch.setattr(_herdr_backend, "_session_entries", fake_session_entries)
    monkeypatch.setattr(_herdr_backend, "_new_session_name", lambda: "fresh")
    monkeypatch.setattr(_herdr_backend, "interactive_choose_with_preview", fake_interactive_choose_with_preview)

    action, payload = _herdr_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
    )

    assert action == "handoff_script"
    assert payload == "herdr session stop alpha --json\nherdr session stop beta --json\nherdr --session fresh"


def test_kill_interactive_shows_only_running_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_options: list[list[str]] = []

    def fake_session_entries() -> list[_herdr_backend.JsonObject]:
        return [
            _session(name="running", running=True),
            _session(name="stopped", running=False),
        ]

    def fake_interactive_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool,
    ) -> list[str] | str | None:
        observed_options.append(list(options_to_preview_mapping))
        return ["running"]

    monkeypatch.setattr(_herdr_backend, "_session_entries", fake_session_entries)
    monkeypatch.setattr(_herdr_backend, "interactive_choose_with_preview", fake_interactive_choose_with_preview)

    action, payload, killed_targets = _herdr_backend.choose_kill_target(
        name=None,
        kill_all=False,
        idle=False,
        window=False,
        delete=False,
    )

    assert action == "run_script"
    assert payload == "herdr session stop running --json"
    assert killed_targets == []
    assert observed_options == [["running"]]


def test_kill_delete_interactive_shows_only_stopped_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_options: list[list[str]] = []

    def fake_session_entries() -> list[_herdr_backend.JsonObject]:
        return [
            _session(name="running", running=True),
            _session(name="stopped", running=False),
        ]

    def fake_interactive_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool,
    ) -> list[str] | str | None:
        observed_options.append(list(options_to_preview_mapping))
        return ["[stopped] SESSION (stopped)"]

    monkeypatch.setattr(_herdr_backend, "_session_entries", fake_session_entries)
    monkeypatch.setattr(_herdr_backend, "interactive_choose_with_preview", fake_interactive_choose_with_preview)

    action, payload, killed_targets = _herdr_backend.choose_kill_target(
        name=None,
        kill_all=False,
        idle=False,
        window=False,
        delete=True,
    )

    assert action == "run_script"
    assert payload == "herdr session delete stopped --json"
    assert killed_targets == []
    assert observed_options == [["[stopped] SESSION (stopped)"]]


def test_kill_delete_all_deletes_stopped_sessions_only(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_session_entries() -> list[_herdr_backend.JsonObject]:
        return [
            _session(name="running", running=True),
            _session(name="stopped-a", running=False),
            _session(name="stopped-b", running=False),
        ]

    monkeypatch.setattr(_herdr_backend, "_session_entries", fake_session_entries)

    action, payload, killed_targets = _herdr_backend.choose_kill_target(
        name=None,
        kill_all=True,
        idle=False,
        window=False,
        delete=True,
    )

    assert action == "run_script"
    assert payload == "herdr session delete stopped-a --json\nherdr session delete stopped-b --json"
    assert killed_targets == []


def test_named_stopped_session_can_only_be_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_session_entries() -> list[_herdr_backend.JsonObject]:
        return [_session(name="stopped", running=False)]

    monkeypatch.setattr(_herdr_backend, "_session_entries", fake_session_entries)

    action, payload, killed_targets = _herdr_backend.choose_kill_target(
        name="stopped",
        kill_all=False,
        idle=False,
        window=False,
        delete=False,
    )
    assert action == "error"
    assert payload == "Herdr session 'stopped' is stopped and cannot be killed."
    assert killed_targets == []

    action, payload, killed_targets = _herdr_backend.choose_kill_target(
        name="stopped",
        kill_all=False,
        idle=False,
        window=False,
        delete=True,
    )
    assert action == "run_script"
    assert payload == "herdr session delete stopped --json"
    assert killed_targets == []
