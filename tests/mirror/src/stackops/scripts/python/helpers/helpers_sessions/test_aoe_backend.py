import pytest

from stackops.scripts.python.helpers.helpers_sessions import _aoe_backend
from stackops.scripts.python.helpers.helpers_sessions.terminal_cli_helpers import resolve_session_backend


def _session(title: str, status: str = "running") -> _aoe_backend.JsonObject:
    return {"title": title, "id": f"id-{title}", "status": status}


def test_resolve_session_backend_accepts_aoe_aliases() -> None:
    assert resolve_session_backend("aoe") == "aoe"
    assert resolve_session_backend("e") == "aoe"


def test_attach_interactive_aoe_session(monkeypatch: pytest.MonkeyPatch) -> None:
    observed_options: list[list[str]] = []

    def fake_interactive_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool = False,
    ) -> list[str] | str | None:
        assert msg == "Choose an AoE session to attach to:"
        assert multi is False
        observed_options.append(list(options_to_preview_mapping))
        return "alpha"

    monkeypatch.setattr(_aoe_backend, "_session_entries", lambda: [_session("alpha")])
    monkeypatch.setattr(_aoe_backend, "interactive_choose_with_preview", fake_interactive_choose_with_preview)

    action, payload = _aoe_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
    )

    assert action == "handoff_script"
    assert payload == "aoe session attach alpha"
    assert observed_options == [["alpha"]]


def test_attach_named_aoe_session_skips_listing() -> None:
    action, payload = _aoe_backend.choose_session(
        name="alpha",
        new_session=False,
        kill_all=False,
        window=False,
    )

    assert action == "handoff_script"
    assert payload == "aoe session attach alpha"


def test_attach_rejects_aoe_window_targets() -> None:
    action, payload = _aoe_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=True,
    )

    assert action == "error"
    assert payload == "AoE backend only supports session-level attach."


def test_kill_all_stops_killable_aoe_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        _aoe_backend,
        "_session_entries",
        lambda: [
            _session("alpha", "running"),
            _session("beta", "stopped"),
            _session("gamma", "waiting"),
        ],
    )

    action, payload, killed_targets = _aoe_backend.choose_kill_target(
        name=None,
        kill_all=True,
        idle=False,
        window=False,
    )

    assert action == "run_script"
    assert payload == "aoe session stop alpha\naoe session stop gamma"
    assert killed_targets == [
        {"action": "session", "session": "alpha", "window": "-", "detail": "-"},
        {"action": "session", "session": "gamma", "window": "-", "detail": "-"},
    ]


def test_kill_interactive_aoe_session(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_interactive_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool,
    ) -> list[str]:
        assert msg == "Choose an AoE session to kill:"
        assert multi is True
        assert list(options_to_preview_mapping) == ["alpha", "gamma"]
        return ["gamma"]

    monkeypatch.setattr(
        _aoe_backend,
        "_session_entries",
        lambda: [
            _session("alpha", "running"),
            _session("beta", "stopped"),
            _session("gamma", "waiting"),
        ],
    )
    monkeypatch.setattr(_aoe_backend, "interactive_choose_with_preview", fake_interactive_choose_with_preview)

    action, payload, killed_targets = _aoe_backend.choose_kill_target(
        name=None,
        kill_all=False,
        idle=False,
        window=False,
    )

    assert action == "run_script"
    assert payload == "aoe session stop gamma"
    assert killed_targets == [
        {"action": "session", "session": "gamma", "window": "-", "detail": "-"},
    ]
