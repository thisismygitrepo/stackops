from __future__ import annotations

from pathlib import Path
import sys
import time as time_module
from types import ModuleType
from typing import cast

import pytest

from machineconfig.cluster.sessions_managers.session_conflict import SessionConflictAction
from machineconfig.cluster.sessions_managers.session_exit_mode import SessionExitMode
from machineconfig.scripts.python.helpers.helpers_sessions import sessions_impl as subject
from machineconfig.utils.schemas.layouts.layout_types import LayoutConfig


def install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    module: ModuleType,
) -> None:
    monkeypatch.setitem(sys.modules, name, module)


def test_select_layout_strips_comments_and_matches_case_insensitively(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layouts_file = tmp_path / "layouts.json"
    layouts_file.write_text(
        """/*comment*/{"layouts":[{"layoutName":"Alpha","layoutTabs":[{"tabName":"one","startDir":".","command":"echo 1"}]}]}""",
        encoding="utf-8",
    )
    io_module = ModuleType("machineconfig.utils.io")

    def remove_c_style_comments(text: str) -> str:
        return text.replace("/*comment*/", "")

    setattr(io_module, "remove_c_style_comments", remove_c_style_comments)
    install_module(monkeypatch, "machineconfig.utils.io", io_module)

    selected = subject.select_layout(
        layouts_json_file=str(layouts_file),
        selected_layouts_names=["alpha"],
        select_interactively=False,
    )

    assert [layout["layoutName"] for layout in selected] == ["Alpha"]


def test_find_layout_file_returns_match_for_missing_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_helper_module = ModuleType("machineconfig.utils.path_helper")
    options_module = ModuleType("machineconfig.utils.options")

    def sanitize_path(layout_path: str) -> Path:
        return tmp_path / layout_path

    def match_file_name(
        sub_string: str,
        search_root: Path,
        suffixes: set[str],
    ) -> Path:
        assert sub_string == "missing-layout"
        assert search_root == Path.cwd()
        assert suffixes == {".json"}
        return tmp_path / "picked.json"

    def search_for_files_of_interest(
        path_obj: Path,
        suffixes: set[str],
    ) -> list[str]:
        raise AssertionError(f"unexpected directory search: {path_obj} {suffixes}")

    def choose_from_options(
        multi: bool,
        options: list[str],
        tv: bool,
        msg: str,
    ) -> str | None:
        raise AssertionError(f"unexpected chooser call: {multi} {options} {tv} {msg}")

    setattr(path_helper_module, "sanitize_path", sanitize_path)
    setattr(path_helper_module, "match_file_name", match_file_name)
    setattr(path_helper_module, "search_for_files_of_interest", search_for_files_of_interest)
    setattr(options_module, "choose_from_options", choose_from_options)
    install_module(monkeypatch, "machineconfig.utils.path_helper", path_helper_module)
    install_module(monkeypatch, "machineconfig.utils.options", options_module)

    result = subject.find_layout_file(layout_path="missing-layout")

    assert result == str(tmp_path / "picked.json")


def test_resolve_conflicts_for_batch_skips_restarts_and_renames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    layouts_batch: list[LayoutConfig] = [
        {"layoutName": "Alpha", "layoutTabs": []},
        {"layoutName": "Beta", "layoutTabs": [{"tabName": "tab", "startDir": ".", "command": "echo"}]},
        {"layoutName": "Gamma", "layoutTabs": []},
    ]
    launch_plan: list[dict[str, object]] = [
        {"session_name": "Alpha", "restart_required": False, "skip_launch": True},
        {"session_name": "Beta-renamed", "restart_required": True},
        {"session_name": "Gamma", "restart_required": False},
    ]

    def fake_build_session_launch_plan(
        requested_session_names: list[str],
        backend: subject.BackendName,
        on_conflict: SessionConflictAction,
    ) -> list[dict[str, object]]:
        assert requested_session_names == ["Alpha", "Beta", "Gamma"]
        assert backend == "windows-terminal"
        assert on_conflict == cast(SessionConflictAction, "rename")
        return launch_plan

    monkeypatch.setattr(subject, "build_session_launch_plan", fake_build_session_launch_plan)

    layouts_to_run, sessions_to_restart = subject.resolve_conflicts_for_batch(
        layouts_batch=layouts_batch,
        backend="windows-terminal",
        on_conflict=cast(SessionConflictAction, "rename"),
    )

    assert sessions_to_restart == {"Beta-renamed"}
    assert [layout["layoutName"] for layout in layouts_to_run] == ["Beta-renamed", "Gamma"]
    assert layouts_to_run[0]["layoutTabs"] == layouts_batch[1]["layoutTabs"]


def test_run_layouts_windows_terminal_batches_and_restarts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    layouts_selected: list[LayoutConfig] = [
        {"layoutName": "One", "layoutTabs": []},
        {"layoutName": "Two", "layoutTabs": []},
    ]
    killed_sessions: list[tuple[str, str]] = []
    initialized_batches: list[list[str]] = []
    monitor_waits: list[int] = []
    killed_managers: list[str] = []
    slept_seconds: list[float] = []
    resolve_calls: list[list[str]] = []

    def fake_resolve_conflicts_for_batch(
        layouts_batch: list[LayoutConfig],
        backend: subject.BackendName,
        on_conflict: SessionConflictAction,
    ) -> tuple[list[LayoutConfig], set[str]]:
        resolve_calls.append([layout["layoutName"] for layout in layouts_batch])
        assert backend == "windows-terminal"
        assert on_conflict == cast(SessionConflictAction, "rename")
        if len(resolve_calls) == 1:
            return ([{"layoutName": "RunMe", "layoutTabs": []}], {"restart-me"})
        return ([], set())

    def fake_kill_existing_session(backend: str, session_name: str) -> None:
        killed_sessions.append((backend, session_name))

    class FakeWTLocalManager:
        def __init__(
            self,
            session_layouts: list[LayoutConfig],
            session_name_prefix: str | None,
            exit_mode: SessionExitMode,
        ) -> None:
            assert session_name_prefix is None
            assert exit_mode == cast(SessionExitMode, "stayOpen")
            initialized_batches.append([layout["layoutName"] for layout in session_layouts])

        def start_all_sessions(self) -> dict[str, dict[str, object]]:
            return {"RunMe": {"success": True}}

        def run_monitoring_routine(self, wait_ms: int) -> None:
            monitor_waits.append(wait_ms)

        def kill_all_sessions(self) -> None:
            killed_managers.append("killed")

    wt_module = ModuleType("machineconfig.cluster.sessions_managers.windows_terminal.wt_local_manager")
    setattr(wt_module, "WTLocalManager", FakeWTLocalManager)
    install_module(
        monkeypatch,
        "machineconfig.cluster.sessions_managers.windows_terminal.wt_local_manager",
        wt_module,
    )
    monkeypatch.setattr(subject, "resolve_conflicts_for_batch", fake_resolve_conflicts_for_batch)
    monkeypatch.setattr(subject, "kill_existing_session", fake_kill_existing_session)
    monkeypatch.setattr(
        time_module,
        "sleep",
        lambda seconds: slept_seconds.append(seconds),
    )

    subject.run_layouts(
        sleep_inbetween=1.25,
        monitor=False,
        parallel_layouts=1,
        kill_upon_completion=True,
        backend="windows-terminal",
        on_conflict=cast(SessionConflictAction, "rename"),
        exit_mode=cast(SessionExitMode, "stayOpen"),
        layouts_selected=layouts_selected,
    )

    assert resolve_calls == [["One"], ["Two"]]
    assert killed_sessions == [("windows-terminal", "restart-me")]
    assert initialized_batches == [["RunMe"]]
    assert monitor_waits == [2000]
    assert killed_managers == ["killed"]
    assert slept_seconds == [1.25]
    assert "--parallel-layouts implies --monitor" in capsys.readouterr().out


def test_run_layouts_rejects_invalid_options() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        subject.run_layouts(
            sleep_inbetween=0.1,
            monitor=False,
            parallel_layouts=0,
            kill_upon_completion=False,
            backend="tmux",
            on_conflict=cast(SessionConflictAction, "error"),
            exit_mode=cast(SessionExitMode, "backToShell"),
            layouts_selected=[],
        )

    with pytest.raises(ValueError, match="currently supported only for tmux and windows-terminal"):
        subject.run_layouts(
            sleep_inbetween=0.1,
            monitor=False,
            parallel_layouts=None,
            kill_upon_completion=False,
            backend="zellij",
            on_conflict=cast(SessionConflictAction, "error"),
            exit_mode=cast(SessionExitMode, "stayOpen"),
            layouts_selected=[],
        )
