from __future__ import annotations

from subprocess import CompletedProcess

import pytest

from machineconfig.scripts.python.helpers.helpers_sessions import _tmux_backend_preview as tmux_preview


def _completed_process(stdout: str, returncode: int, stderr: str) -> CompletedProcess[str]:
    return CompletedProcess(args=["tmux"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_collect_session_snapshot_sorts_windows_and_panes() -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        if args[1] == "list-windows":
            return _completed_process(stdout="10\tlogs\t1\t\n2\teditor\t2\tactive\n", returncode=0, stderr="")
        if args[1] == "list-panes":
            return _completed_process(
                stdout="2\t5\t/tmp\tbash\t\t\t\t55\n2\t1\t/proj\tvim\tactive\t\t\t56\n10\t0\t/var\tsh\t\tdead\t1\t57\n", returncode=0, stderr=""
            )
        raise AssertionError(f"unexpected command: {args}")

    windows, panes_by_window, pane_warning = tmux_preview.collect_session_snapshot(session_name="main", run_command_fn=fake_run_command)

    assert [window["window_index"] for window in windows or []] == ["2", "10"]
    assert [pane["pane_index"] for pane in panes_by_window["2"]] == ["1", "5"]
    assert pane_warning is None


def test_collect_session_snapshot_returns_error_when_window_query_fails() -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        del args
        return _completed_process(stdout="", returncode=1, stderr="tmux server missing")

    windows, panes_by_window, pane_warning = tmux_preview.collect_session_snapshot(session_name="main", run_command_fn=fake_run_command)

    assert windows is None
    assert panes_by_window == {}
    assert pane_warning == "tmux server missing"


def test_build_preview_includes_tables_and_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_collect_session_snapshot(
        session_name: str, run_command_fn: object
    ) -> tuple[list[dict[str, str]] | None, dict[str, list[dict[str, str]]], str | None]:
        del session_name, run_command_fn
        return (
            [{"window_index": "1", "window_name": "editor", "window_panes": "1", "window_active": "active"}],
            {
                "1": [
                    {
                        "pane_index": "0",
                        "pane_cwd": "/tmp/project",
                        "pane_command": "vim",
                        "pane_active": "active",
                        "pane_dead": "",
                        "pane_dead_status": "",
                        "pane_pid": "200",
                    }
                ]
            },
            "pane list partial",
        )

    def fake_classify(_: dict[str, str]) -> tuple[str, str]:
        return ("vim", "running: `vim`")

    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(tmux_preview, "collect_session_snapshot", fake_collect_session_snapshot)

    preview = tmux_preview.build_preview(session_name="main", run_command_fn=fake_run_command, classify_pane_status_fn=fake_classify)

    assert "# Session: main" in preview
    assert "| 1 | editor | 1 | **yes** |" in preview
    assert "| 1 | editor | 0 ⇐ | vim | running: `vim` | `/tmp/project` |" in preview
    assert "> ⚠ pane query warning: pane list partial" in preview


def test_window_and_pane_previews_render_runtime_state() -> None:
    def fake_classify(_: dict[str, str]) -> tuple[str, str]:
        return ("shell", "idle shell")

    window_preview = tmux_preview.build_window_preview(
        session_name="main",
        window={"window_index": "2", "window_name": "logs", "window_panes": "0", "window_active": ""},
        panes=[],
        pane_warning="pane data unavailable",
        classify_pane_status_fn=fake_classify,
    )
    pane_preview = tmux_preview.build_pane_preview(
        session_name="main",
        window={"window_index": "2", "window_name": "logs", "window_panes": "1", "window_active": ""},
        pane={
            "pane_index": "3",
            "pane_cwd": "",
            "pane_command": "bash",
            "pane_active": "",
            "pane_dead": "",
            "pane_dead_status": "",
            "pane_pid": "200",
        },
        classify_pane_status_fn=fake_classify,
    )

    assert "| — | — | — | — |" in window_preview
    assert "> ⚠ pane query warning: pane data unavailable" in window_preview
    assert "- Directory: `—`" in pane_preview
    assert "- Active: no" in pane_preview
