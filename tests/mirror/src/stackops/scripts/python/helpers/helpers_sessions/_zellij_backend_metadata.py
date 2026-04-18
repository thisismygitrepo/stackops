from __future__ import annotations

import os
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from stackops.scripts.python.helpers.helpers_sessions import _zellij_backend_metadata as metadata_backend


def _completed_process(stdout: str, returncode: int, stderr: str) -> CompletedProcess[str]:
    return CompletedProcess(args=["zellij"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_find_latest_session_info_file_selects_newest_candidate(tmp_path: Path) -> None:
    older = tmp_path / ".cache" / "zellij" / "a" / "session_info" / "proj" / "session-layout.kdl"
    newer = tmp_path / ".cache" / "zellij" / "b" / "session_info" / "proj" / "session-layout.kdl"
    older.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    older.write_text("old", encoding="utf-8")
    newer.write_text("new", encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    with patch.object(metadata_backend.Path, "home", return_value=tmp_path):
        result = metadata_backend.find_latest_session_info_file("proj", "session-layout.kdl")

    assert result == newer


def test_read_session_metadata_parses_and_sorts_entries(tmp_path: Path) -> None:
    session_file = tmp_path / "session-metadata.kdl"
    session_file.write_text(
        """
        tabs {
            tab {
                position 1
                name "Logs"
            }
            tab {
                position 0
                name "Main"
                active true
            }
        }
        panes {
            pane {
                id 5
                tab_position 1
                pane_x 10
                pane_y 0
                title "tail"
                is_selectable true
                is_plugin false
            }
            pane {
                id 2
                tab_position 0
                pane_x 5
                pane_y 0
                title "Editor"
                is_selectable true
                is_plugin false
            }
            pane {
                id 1
                tab_position 0
                pane_x 0
                pane_y 0
                title "Shell"
                is_selectable true
                is_plugin false
                is_focused true
            }
        }
        """,
        encoding="utf-8",
    )

    with patch.object(metadata_backend, "find_latest_session_info_file", return_value=session_file):
        parsed = metadata_backend.read_session_metadata("proj")

    assert parsed is not None
    tabs, panes = parsed
    assert [tab["name"] for tab in tabs] == ["Main", "Logs"]
    assert tabs[0]["active"] is True
    assert [pane["id"] for pane in panes] == [1, 2, 5]


def test_build_metadata_summary_marks_active_focus_and_shell_fallback() -> None:
    summary = metadata_backend.build_metadata_summary(
        tabs=[{"name": "Main", "position": 0, "active": True}, {"name": "Logs", "position": 1}],
        panes=[{"id": 1, "tab_position": 0, "title": "Editor", "is_selectable": True, "is_plugin": False, "is_focused": True, "is_floating": True}],
    )

    assert summary == "\n".join(["tabs: 2", "[1] Main *", "  - Editor (focused, floating)", "[2] Logs", "  - shell"])


def test_get_live_tab_names_trims_blank_lines_and_handles_failures() -> None:
    def fake_run_command(args: list[str]) -> CompletedProcess[str]:
        assert args == ["zellij", "--session", "proj", "action", "query-tab-names"]
        return _completed_process(stdout="code\n\nlogs\n", returncode=0, stderr="")

    def fake_run_command_failure(args: list[str]) -> CompletedProcess[str]:
        assert args == ["zellij", "--session", "proj", "action", "query-tab-names"]
        return _completed_process(stdout="", returncode=1, stderr="no session")

    assert metadata_backend.get_live_tab_names("proj", run_command_fn=fake_run_command) == ["code", "logs"]
    assert metadata_backend.get_live_tab_names("proj", run_command_fn=fake_run_command_failure) == []
