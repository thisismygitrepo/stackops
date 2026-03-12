from subprocess import CompletedProcess

from machineconfig.scripts.python.helpers.helpers_sessions import _tmux_backend, _zellij_backend


def test_tmux_window_mode_selects_pane_target(monkeypatch) -> None:
    def fake_run_command(args: list[str], timeout: float = 5.0) -> CompletedProcess[str]:
        if args == ["tmux", "list-sessions", "-F", "#S"]:
            return CompletedProcess(args=args, returncode=0, stdout="demo\n", stderr="")
        if args[:4] == ["tmux", "list-windows", "-t", "demo"]:
            return CompletedProcess(args=args, returncode=0, stdout="0\teditor\t2\tactive\n", stderr="")
        if args[:5] == ["tmux", "list-panes", "-s", "-t", "demo"]:
            return CompletedProcess(
                args=args,
                returncode=0,
                stdout=(
                    "0\t0\t/tmp\tbash\tactive\t\t\t1111\n"
                    "0\t1\t/tmp/project\tpython\t\t\t\t2222\n"
                ),
                stderr="",
            )
        raise AssertionError(f"Unexpected command: {args}")

    def fake_choose_with_preview(msg: str, options_to_preview_mapping: dict[str, str]) -> str:
        assert msg == "Choose a tmux window or pane to attach to:"
        return next(label for label in options_to_preview_mapping if label.endswith(".1 python"))

    monkeypatch.setattr(_tmux_backend, "run_command", fake_run_command)
    monkeypatch.setattr(_tmux_backend, "interactive_choose_with_preview", fake_choose_with_preview)

    action, script = _tmux_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=True,
    )

    assert action == "run_script"
    assert script == "tmux select-window -t demo:0\ntmux select-pane -t demo:0.1\ntmux attach -t demo"


def test_zellij_window_mode_selects_pane_with_focus_path(monkeypatch) -> None:
    def fake_run_command(args: list[str], timeout: float = 5.0) -> CompletedProcess[str]:
        if args == ["zellij", "list-sessions"]:
            return CompletedProcess(args=args, returncode=0, stdout="demo [Created 2026-03-12 00:00:00]\n", stderr="")
        raise AssertionError(f"Unexpected command: {args}")

    def fake_choose_with_preview(msg: str, options_to_preview_mapping: dict[str, str]) -> str:
        assert msg == "Choose a Zellij tab or pane to attach to:"
        return next(label for label in options_to_preview_mapping if "Right Pane" in label)

    monkeypatch.setattr(_zellij_backend, "run_command", fake_run_command)
    monkeypatch.setattr(_zellij_backend, "interactive_choose_with_preview", fake_choose_with_preview)
    monkeypatch.setattr(
        _zellij_backend,
        "_read_session_metadata",
        lambda session_name: (
            [{"position": 0, "name": "work", "active": True}],
            [
                {
                    "id": 1,
                    "title": "Left Pane",
                    "tab_position": 0,
                    "is_selectable": True,
                    "is_plugin": False,
                    "exited": False,
                    "is_suppressed": False,
                    "is_focused": True,
                    "is_floating": False,
                    "pane_x": 0,
                    "pane_y": 0,
                    "pane_columns": 80,
                    "pane_rows": 20,
                },
                {
                    "id": 2,
                    "title": "Right Pane",
                    "tab_position": 0,
                    "is_selectable": True,
                    "is_plugin": False,
                    "exited": False,
                    "is_suppressed": False,
                    "is_focused": False,
                    "is_floating": False,
                    "pane_x": 80,
                    "pane_y": 0,
                    "pane_columns": 80,
                    "pane_rows": 20,
                },
            ],
        ),
    )

    action, script = _zellij_backend.choose_session(
        name=None,
        new_session=False,
        kill_all=False,
        window=True,
    )

    assert action == "run_script"
    assert script == (
        "zellij --session demo action go-to-tab-name work\n"
        "zellij --session demo action move-focus right\n"
        "zellij attach demo"
    )
