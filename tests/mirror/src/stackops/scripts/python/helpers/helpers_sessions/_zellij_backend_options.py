from __future__ import annotations

from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_sessions import _zellij_backend_options as options_backend


type SessionMetadata = tuple[list[dict[str, object]], list[dict[str, object]]]


def _quote(value: str | Path) -> str:
    return f"<{value}>"


def test_attach_and_kill_scripts_include_focus_actions() -> None:
    attach_script = options_backend.attach_script_for_target(
        session_name="work",
        quote_fn=_quote,
        tab_name="code",
        pane_focus_commands=["right", "down"],
    )
    session_kill = options_backend.kill_script_for_target(session_name="work", quote_fn=_quote)
    tab_kill = options_backend.kill_script_for_target(session_name="work", quote_fn=_quote, tab_name="code")
    pane_kill = options_backend.kill_script_for_target(
        session_name="work",
        quote_fn=_quote,
        tab_name="code",
        pane_focus_commands=["left"],
        kill_pane=True,
    )

    assert attach_script == "\n".join(
        [
            "zellij --session <work> action go-to-tab-name <code>",
            "zellij --session <work> action move-focus right",
            "zellij --session <work> action move-focus down",
            "zellij attach <work>",
        ]
    )
    assert session_kill == "zellij delete-session --force <work>"
    assert tab_kill == "\n".join(
        [
            "zellij --session <work> action go-to-tab-name <code>",
            "zellij --session <work> action close-tab",
        ]
    )
    assert pane_kill == "\n".join(
        [
            "zellij --session <work> action go-to-tab-name <code>",
            "zellij --session <work> action move-focus left",
            "zellij --session <work> action close-pane",
        ]
    )
    with pytest.raises(ValueError, match="pane_focus_commands must be provided"):
        options_backend.kill_script_for_target(
            session_name="work",
            quote_fn=_quote,
            tab_name="code",
            pane_focus_commands=None,
            kill_pane=True,
        )


def test_build_window_target_options_uses_metadata_for_tabs_and_panes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tabs: list[dict[str, object]] = [{"name": "Main", "position": 0, "active": True}]
    panes: list[dict[str, object]] = [
        {"id": 1, "title": "Editor", "is_focused": True, "is_floating": False},
        {"id": 2, "title": "Shell", "is_focused": False, "is_floating": True},
    ]

    def fake_selectable_panes_for_tab(all_panes: list[dict[str, object]], tab_position: int) -> list[dict[str, object]]:
        assert all_panes == panes
        assert tab_position == 0
        return panes

    def fake_focus_path_to_pane(all_panes: list[dict[str, object]], target_pane: dict[str, object]) -> list[str] | None:
        assert all_panes == panes
        if target_pane["id"] == 1:
            return []
        return ["right"]

    def fake_read_session_metadata(_session_name: str) -> SessionMetadata:
        return (tabs, panes)

    monkeypatch.setattr(options_backend, "selectable_panes_for_tab", fake_selectable_panes_for_tab)
    monkeypatch.setattr(options_backend, "focus_path_to_pane", fake_focus_path_to_pane)

    scripts, previews = options_backend.build_window_target_options(
        active_sessions=["s1"],
        read_session_metadata_fn=fake_read_session_metadata,
        get_live_tab_names_fn=lambda _session_name: [],
        quote_fn=_quote,
    )

    assert scripts["[s1] 1:Main *"] == "zellij --session <s1> action go-to-tab-name <Main>\nzellij attach <s1>"
    assert scripts["[s1] 1:Main / Editor *"] == "zellij --session <s1> action go-to-tab-name <Main>\nzellij attach <s1>"
    assert scripts["[s1] 1:Main / Shell"] == "\n".join(
        [
            "zellij --session <s1> action go-to-tab-name <Main>",
            "zellij --session <s1> action move-focus right",
            "zellij attach <s1>",
        ]
    )
    assert "panes: 2" in previews["[s1] 1:Main *"]
    assert "- Shell (floating)" in previews["[s1] 1:Main *"]
    assert "focus plan: already focused in this tab" in previews["[s1] 1:Main / Editor *"]
    assert "focus plan: move-focus right" in previews["[s1] 1:Main / Shell"]


def test_build_window_target_options_falls_back_to_live_tab_names() -> None:
    scripts, previews = options_backend.build_window_target_options(
        active_sessions=["s1"],
        read_session_metadata_fn=lambda _session_name: None,
        get_live_tab_names_fn=lambda _session_name: ["Main", "Logs"],
        quote_fn=_quote,
    )

    assert scripts == {
        "[s1] 1:Main": "zellij --session <s1> action go-to-tab-name <Main>\nzellij attach <s1>",
        "[s1] 2:Logs": "zellij --session <s1> action go-to-tab-name <Logs>\nzellij attach <s1>",
    }
    assert "Pane metadata is unavailable for this session." in previews["[s1] 1:Main"]


def test_build_kill_target_options_skips_panes_without_focus_path(monkeypatch: pytest.MonkeyPatch) -> None:
    tabs: list[dict[str, object]] = [{"name": "Main", "position": 0, "active": True}]
    panes: list[dict[str, object]] = [
        {"id": 1, "title": "Editor", "is_focused": True, "is_floating": False},
        {"id": 2, "title": "Shell", "is_focused": False, "is_floating": False},
    ]

    def fake_read_session_metadata(_session_name: str) -> SessionMetadata:
        return (tabs, panes)

    monkeypatch.setattr(options_backend, "selectable_panes_for_tab", lambda _panes, _tab_position: panes)
    monkeypatch.setattr(
        options_backend,
        "focus_path_to_pane",
        lambda _panes, target_pane: [] if target_pane["id"] == 1 else None,
    )

    scripts, previews = options_backend.build_kill_target_options(
        active_sessions=["s1"],
        read_session_metadata_fn=fake_read_session_metadata,
        get_live_tab_names_fn=lambda _session_name: [],
        quote_fn=_quote,
    )

    assert set(scripts) == {"[s1] 1:Main *", "[s1] 1:Main / Editor *"}
    assert scripts["[s1] 1:Main *"] == "zellij --session <s1> action go-to-tab-name <Main>\nzellij --session <s1> action close-tab"
    assert scripts["[s1] 1:Main / Editor *"] == "zellij --session <s1> action go-to-tab-name <Main>\nzellij --session <s1> action close-pane"
    assert "focus plan: already focused in this tab" in previews["[s1] 1:Main / Editor *"]
