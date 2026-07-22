import pytest

from stackops.scripts.python.helpers.helpers_sessions import _herdr_backend


type Command = tuple[str, ...]


def _window_payloads(*, first_space_name: str, second_space_name: str, focused: bool) -> dict[Command, _herdr_backend.JsonObject]:
    return {
        ("herdr", "session", "list", "--json"): {"sessions": [{"default": True, "name": "demo", "running": True}]},
        ("herdr", "--session", "demo", "workspace", "list"): {
            "result": {"workspaces": [{"label": first_space_name, "workspace_id": "w1"}, {"label": second_space_name, "workspace_id": "w2"}]}
        },
        ("herdr", "--session", "demo", "tab", "list"): {
            "result": {
                "tabs": [
                    {"focused": focused, "label": "main", "number": 1, "tab_id": "w1:t1", "workspace_id": "w1"},
                    {"focused": False, "label": "main", "number": 1, "tab_id": "w2:t1", "workspace_id": "w2"},
                ]
            }
        },
        ("herdr", "--session", "demo", "pane", "list"): {
            "result": {
                "panes": [
                    {"agent": "codex", "focused": focused, "pane_id": "w1:p1", "tab_id": "w1:t1", "terminal_id": "term-one", "workspace_id": "w1"},
                    {"agent": "codex", "focused": False, "pane_id": "w1:p2", "tab_id": "w1:t1", "terminal_id": "term-one-b", "workspace_id": "w1"},
                    {"agent": "codex", "focused": False, "pane_id": "w2:p1", "tab_id": "w2:t1", "terminal_id": "term-two", "workspace_id": "w2"},
                ]
            }
        },
    }


def _install_json_responses(*, monkeypatch: pytest.MonkeyPatch, payloads: dict[Command, _herdr_backend.JsonObject]) -> list[Command]:
    calls: list[Command] = []

    def run_json_command(args: list[str]) -> _herdr_backend.JsonObject | None:
        command = tuple(args)
        calls.append(command)
        payload = payloads.get(command)
        if payload is None:
            raise AssertionError(f"Unexpected Herdr command: {command}")
        return payload

    monkeypatch.setattr(_herdr_backend, "_run_json_command", run_json_command)
    return calls


def test_window_attach_shows_space_name_in_selection_and_preview(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _install_json_responses(
        monkeypatch=monkeypatch,
        payloads=_window_payloads(first_space_name="alpha", second_space_name="beta", focused=False),
    )
    captured_previews: dict[str, str] = {}
    selected_label = "[demo] [space: beta (w2)] 1:main [w2:t1]"
    alpha_pane_label = "[demo] [space: alpha (w1)] 1:main / codex [w1:p1]"

    def select_target(msg: str, options_to_preview_mapping: dict[str, str]) -> str:
        assert msg == "Choose a Herdr tab or pane to attach to:"
        captured_previews.update(options_to_preview_mapping)
        return selected_label

    monkeypatch.setattr(_herdr_backend, "interactive_choose_with_preview", select_target)

    action, script = _herdr_backend.choose_session(name=None, new_session=False, kill_all=False, window=True)

    assert action == "handoff_script"
    assert script == "herdr --session demo tab focus w2:t1\nherdr session attach demo"
    assert ("herdr", "--session", "demo", "workspace", "list") in calls
    assert "[demo] [space: alpha (w1)] 1:main [w1:t1]" in captured_previews
    assert selected_label in captured_previews
    assert alpha_pane_label in captured_previews
    assert "[demo] [space: alpha (w1)] 1:main / codex [w1:p2]" in captured_previews
    assert "[demo] [space: beta (w2)] 1:main / codex [w2:p1]" in captured_previews
    assert "space: beta" in captured_previews[selected_label]
    assert "workspace id: w2" in captured_previews[selected_label]
    assert "tab id: w2:t1" in captured_previews[selected_label]
    assert "space: alpha" in captured_previews[alpha_pane_label]
    assert "workspace id: w1" in captured_previews[alpha_pane_label]


def test_duplicate_space_names_are_disambiguated_by_workspace_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_json_responses(
        monkeypatch=monkeypatch,
        payloads=_window_payloads(first_space_name="shared", second_space_name="shared", focused=False),
    )

    options = _herdr_backend._build_window_target_options(["demo"], for_kill=False)

    assert "[demo] [space: shared (w1)] 1:main [w1:t1]" in options.scripts_by_label
    assert "[demo] [space: shared (w2)] 1:main [w2:t1]" in options.scripts_by_label
    assert len(options.scripts_by_label) == 5


def test_window_kill_uses_explicit_tab_parent_for_pane_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_json_responses(
        monkeypatch=monkeypatch,
        payloads=_window_payloads(first_space_name="alpha / project", second_space_name="beta", focused=True),
    )
    tab_label = "[demo] [space: alpha / project (w1)] 1:main [w1:t1] *"
    pane_label = "[demo] [space: alpha / project (w1)] 1:main / codex [w1:p1] *"

    def select_targets(msg: str, options_to_preview_mapping: dict[str, str], multi: bool) -> list[str]:
        assert msg == "Choose a Herdr session, tab, or pane to kill:"
        assert tab_label in options_to_preview_mapping
        assert pane_label in options_to_preview_mapping
        assert multi is True
        return [tab_label, pane_label]

    monkeypatch.setattr(_herdr_backend, "interactive_choose_with_preview", select_targets)

    action, script, killed_targets = _herdr_backend.choose_kill_target(name=None, kill_all=False, idle=False, window=True, delete=False)

    assert action == "run_script"
    assert script == "herdr --session demo tab close w1:t1"
    assert killed_targets == []


def test_window_kill_scopes_session_parent_suppression_without_parsing_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    first_session_name = "one]broken"
    second_session_name = "two"
    first_session_label = "[one]broken] SESSION (running)"
    first_child_label = "[one]broken] [space: alpha (w1)] 1:main [w1:t1]"
    second_child_label = "[two] [space: beta (w1)] 1:main [w1:t1]"

    def session_entries() -> list[_herdr_backend.JsonObject]:
        return [
            {"default": False, "name": first_session_name, "running": True},
            {"default": False, "name": second_session_name, "running": True},
        ]

    def build_targets(active_sessions: list[str], *, for_kill: bool) -> _herdr_backend._WindowTargetOptions:
        assert active_sessions == [first_session_name, second_session_name]
        assert for_kill is True
        return _herdr_backend._WindowTargetOptions(
            scripts_by_label={
                first_child_label: "close-first-child",
                second_child_label: "close-second-child",
            },
            previews_by_label={first_child_label: "first", second_child_label: "second"},
            tab_parent_by_pane_label={},
            session_name_by_target_label={
                first_child_label: first_session_name,
                second_child_label: second_session_name,
            },
        )

    def select_targets(msg: str, options_to_preview_mapping: dict[str, str], multi: bool) -> list[str]:
        assert msg == "Choose a Herdr session, tab, or pane to kill:"
        assert options_to_preview_mapping
        assert multi is True
        return [first_session_label, first_child_label, second_child_label]

    monkeypatch.setattr(_herdr_backend, "_session_entries", session_entries)
    monkeypatch.setattr(_herdr_backend, "_build_window_target_options", build_targets)
    monkeypatch.setattr(_herdr_backend, "interactive_choose_with_preview", select_targets)

    action, script, killed_targets = _herdr_backend.choose_kill_target(name=None, kill_all=False, idle=False, window=True, delete=False)

    assert action == "run_script"
    assert script == "herdr session stop 'one]broken' --json\nclose-second-child"
    assert killed_targets == []
