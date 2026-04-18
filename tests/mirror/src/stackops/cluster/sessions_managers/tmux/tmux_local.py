from pathlib import Path
import stat
import subprocess
import tempfile

import pytest

from stackops.cluster.sessions_managers.tmux import tmux_local
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def _sample_layout() -> LayoutConfig:
    return {
        "layoutName": "sample_layout",
        "layoutTabs": [
            {"tabName": "editor", "startDir": "/work/app", "command": "nvim"},
            {"tabName": "server", "startDir": "/work/app", "command": "uv run server.py"},
        ],
    }


def test_create_layout_file_writes_executable_script(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    expected_script_path = (
        tmp_path / "tmp_results" / "sessions" / "tmux_layouts" / "layout.sh"
    )

    def fake_home() -> Path:
        return tmp_path

    def fake_mkstemp(suffix: str, dir: Path) -> tuple[int, str]:
        assert suffix == "_layout.sh"
        assert dir == expected_script_path.parent
        return 10, str(expected_script_path)

    def fake_build_tmux_script(
        _layout_config: LayoutConfig,
        _session_name: str,
        _exit_mode: str,
    ) -> str:
        return "#!/usr/bin/env bash\necho ready\n"

    monkeypatch.setattr(tmux_local.Path, "home", fake_home)
    monkeypatch.setattr(tempfile, "mkstemp", fake_mkstemp)
    monkeypatch.setattr(tmux_local, "build_tmux_script", fake_build_tmux_script)

    generator = tmux_local.TmuxLayoutGenerator(
        layout_config=_sample_layout(),
        session_name="alpha",
        exit_mode="backToShell",
    )
    created = generator.create_layout_file()

    assert created is True
    assert generator.script_path == str(expected_script_path)
    assert (
        expected_script_path.read_text(encoding="utf-8")
        == "#!/usr/bin/env bash\necho ready\n"
    )
    assert expected_script_path.stat().st_mode & stat.S_IXUSR


def test_get_status_report_counts_running_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_status(session_name: str) -> tmux_local.TmuxSessionStatus:
        assert session_name == "alpha"
        return {
            "tmux_running": True,
            "session_exists": True,
            "session_name": "alpha",
            "all_sessions": ["alpha"],
        }

    def fake_unknown_status(tab: dict[str, str]) -> dict[str, object]:
        return {
            "running": tab["tabName"] == "editor",
            "command": tab["command"],
        }

    monkeypatch.setattr(tmux_local, "check_tmux_session_status", fake_status)
    monkeypatch.setattr(tmux_local, "build_unknown_command_status", fake_unknown_status)

    generator = tmux_local.TmuxLayoutGenerator(
        layout_config=_sample_layout(),
        session_name="alpha",
        exit_mode="backToShell",
    )
    report = generator.get_status_report()

    assert report["summary"] == {
        "total_commands": 2,
        "running_commands": 1,
        "stopped_commands": 1,
        "session_healthy": True,
    }


def test_prepare_launch_script_uses_merge_builder_for_existing_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written: list[str] = []

    def fake_check_tmux_session_status(
        session_name: str,
    ) -> tmux_local.TmuxSessionStatus:
        return {
            "tmux_running": True,
            "session_exists": True,
            "session_name": session_name,
            "all_sessions": [session_name],
        }

    def fake_build_tmux_merge_script(
        layout_config: LayoutConfig,
        session_name: str,
        on_conflict: str,
        exit_mode: str,
    ) -> str:
        _ = layout_config, session_name, on_conflict, exit_mode
        return "merge-script"

    def fake_write_script_content(script_content: str) -> None:
        written.append(script_content)

    monkeypatch.setattr(
        tmux_local,
        "check_tmux_session_status",
        fake_check_tmux_session_status,
    )
    monkeypatch.setattr(
        tmux_local,
        "build_tmux_merge_script",
        fake_build_tmux_merge_script,
    )

    generator = tmux_local.TmuxLayoutGenerator(
        layout_config=_sample_layout(),
        session_name="alpha",
        exit_mode="terminate",
    )
    monkeypatch.setattr(generator, "_write_script_content", fake_write_script_content)

    generator.prepare_launch_script("mergeNewWindowsSkipMatchingWindows")

    assert written == ["merge-script"]


def test_apply_launch_plan_renames_before_preparing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared: list[str] = []

    def fake_prepare_launch_script(on_conflict: str) -> None:
        prepared.append(on_conflict)

    generator = tmux_local.TmuxLayoutGenerator(
        layout_config=_sample_layout(),
        session_name="alpha",
        exit_mode="backToShell",
    )
    monkeypatch.setattr(generator, "prepare_launch_script", fake_prepare_launch_script)

    generator.apply_launch_plan(
        launch_plan={
            "requested_name": "alpha",
            "session_name": "beta",
            "restart_required": False,
            "conflict_source": "existing",
        },
        on_conflict="rename",
    )

    assert generator.session_name == "beta"
    assert prepared == ["rename"]


def test_run_executes_prepared_script_and_returns_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_build_session_launch_plan(
        requested_session_names: list[str],
        backend: str,
        on_conflict: str,
    ) -> list[tmux_local.SessionLaunchPlan]:
        assert requested_session_names == ["alpha"]
        assert backend == "tmux"
        assert on_conflict == "error"
        return [
            {
                "requested_name": "alpha",
                "session_name": "alpha",
                "restart_required": False,
            }
        ]

    generator = tmux_local.TmuxLayoutGenerator(
        layout_config=_sample_layout(),
        session_name="alpha",
        exit_mode="backToShell",
    )

    def fake_apply_launch_plan(
        launch_plan: tmux_local.SessionLaunchPlan,
        on_conflict: str,
    ) -> None:
        assert launch_plan["session_name"] == "alpha"
        assert on_conflict == "error"
        generator.script_path = "/tmp/generated.sh"

    def fake_run(
        args: list[str],
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text
        assert args == ["bash", "/tmp/generated.sh"]
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(
        tmux_local,
        "build_session_launch_plan",
        fake_build_session_launch_plan,
    )
    monkeypatch.setattr(generator, "apply_launch_plan", fake_apply_launch_plan)
    monkeypatch.setattr(tmux_local.subprocess, "run", fake_run)

    result = generator.run(on_conflict="error")

    assert result == {"returncode": 0, "stdout": "ok", "stderr": ""}
