from typing import NoReturn

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _tmux_backend


def _fail_if_called(*_args: object, **_kwargs: object) -> NoReturn:
    raise AssertionError("Interactive session selection must not run.")


def test_attach_first_session_uses_first_listed_session_without_interaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_list_session_names() -> list[str]:
        return ["beta", "alpha"]

    monkeypatch.setattr(_tmux_backend, "list_session_names", fake_list_session_names)
    monkeypatch.setattr(_tmux_backend, "_build_preview", _fail_if_called)
    monkeypatch.setattr(_tmux_backend, "interactive_choose_with_preview", _fail_if_called)

    action, payload = _tmux_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
        first=True,
    )

    assert action == "handoff_script"
    assert payload == _tmux_backend.attach_script_from_name(name="beta", quote_fn=_tmux_backend.quote)


def test_attach_without_first_keeps_interactive_session_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_messages: list[str] = []

    def fake_list_session_names() -> list[str]:
        return ["beta", "alpha"]

    def fake_build_preview(session_name: str) -> str:
        return f"preview:{session_name}"

    def fake_interactive_choose_with_preview(
        msg: str,
        options_to_preview_mapping: dict[str, str],
        multi: bool = False,
    ) -> str:
        assert multi is False
        assert list(options_to_preview_mapping) == [
            "beta",
            "alpha",
            _tmux_backend.NEW_SESSION_LABEL,
            _tmux_backend.KILL_ALL_AND_NEW_LABEL,
        ]
        observed_messages.append(msg)
        return "alpha"

    monkeypatch.setattr(_tmux_backend, "list_session_names", fake_list_session_names)
    monkeypatch.setattr(_tmux_backend, "_build_preview", fake_build_preview)
    monkeypatch.setattr(
        _tmux_backend,
        "interactive_choose_with_preview",
        fake_interactive_choose_with_preview,
    )

    action, payload = _tmux_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
        first=False,
    )

    assert action == "handoff_script"
    assert payload == _tmux_backend.attach_script_from_name(name="alpha", quote_fn=_tmux_backend.quote)
    assert observed_messages == ["Choose a tmux session to attach to:"]


def test_attach_first_with_no_sessions_starts_new_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_kill_all: list[bool] = []

    def fake_list_session_names() -> list[str]:
        return []

    def fake_new_session_script(kill_all: bool) -> str:
        observed_kill_all.append(kill_all)
        return "new-session"

    monkeypatch.setattr(_tmux_backend, "list_session_names", fake_list_session_names)
    monkeypatch.setattr(_tmux_backend, "new_session_script", fake_new_session_script)
    monkeypatch.setattr(_tmux_backend, "interactive_choose_with_preview", _fail_if_called)

    action, payload = _tmux_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=False,
        first=True,
    )

    assert (action, payload) == ("handoff_script", "new-session")
    assert observed_kill_all == [False]
