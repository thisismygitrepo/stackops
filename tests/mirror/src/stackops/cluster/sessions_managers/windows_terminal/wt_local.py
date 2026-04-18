from pathlib import Path
import subprocess

import pytest

from stackops.cluster.sessions_managers.windows_terminal import wt_local
from stackops.utils.schemas.layouts.layout_types import LayoutConfig


def _layout() -> LayoutConfig:
    return {
        "layoutName": "demo",
        "layoutTabs": [
            {"tabName": "editor", "startDir": "/work/app", "command": "nvim"},
            {"tabName": "monitor", "startDir": "/work/app", "command": "htop"},
        ],
    }


def test_create_layout_file_writes_generated_script(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_generate_random_suffix(_length: int) -> str:
        return "deadbeef"

    def fake_generate_wt_command_string(
        _layout_config: LayoutConfig,
        _session_name: str,
        _exit_mode: str,
    ) -> str:
        return "wt new-tab --title editor"

    monkeypatch.setattr(wt_local, "TMP_LAYOUT_DIR", tmp_path)
    monkeypatch.setattr(
        wt_local,
        "generate_random_suffix",
        fake_generate_random_suffix,
    )
    monkeypatch.setattr(
        wt_local,
        "generate_wt_command_string",
        fake_generate_wt_command_string,
    )

    generator = wt_local.WTLayoutGenerator(
        layout_config=_layout(),
        session_name="demo",
        exit_mode="backToShell",
    )
    created = generator.create_layout_file()

    expected_path = tmp_path / "wt_layout_demo_deadbeef.ps1"
    assert created is True
    assert generator.script_path == str(expected_path)
    file_text = expected_path.read_text(encoding="utf-8")
    assert "Generated with random suffix: deadbeef" in file_text
    assert "wt new-tab --title editor" in file_text


def test_get_wt_layout_preview_uses_preview_session_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_generate_wt_command_string(
        layout_config: LayoutConfig,
        session_name: str,
        exit_mode: str,
    ) -> str:
        assert layout_config == _layout()
        calls.append((session_name, exit_mode))
        return "preview-command"

    monkeypatch.setattr(
        wt_local,
        "generate_wt_command_string",
        fake_generate_wt_command_string,
    )

    generator = wt_local.WTLayoutGenerator(
        layout_config=_layout(),
        session_name="demo",
        exit_mode="terminate",
    )

    assert generator.get_wt_layout_preview(_layout()) == "preview-command"
    assert calls == [("preview", "terminate")]


def test_get_status_report_counts_running_commands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_check_wt_session_status(session_name: str) -> dict[str, object]:
        return {
            "wt_running": True,
            "session_exists": True,
            "session_name": session_name,
            "session_windows": ["editor"],
            "all_windows": ["editor", "monitor"],
        }

    def fake_check_command_status(
        tab_name: str,
        _layout_config: LayoutConfig,
    ) -> dict[str, object]:
        return {
            "running": tab_name == "editor",
            "command": tab_name,
        }

    monkeypatch.setattr(
        wt_local,
        "check_wt_session_status",
        fake_check_wt_session_status,
    )
    monkeypatch.setattr(
        wt_local,
        "check_command_status",
        fake_check_command_status,
    )

    generator = wt_local.WTLayoutGenerator(
        layout_config=_layout(),
        session_name="demo",
        exit_mode="backToShell",
    )
    report = generator.get_status_report()

    assert report["summary"] == {
        "total_commands": 2,
        "running_commands": 1,
        "stopped_commands": 1,
        "session_healthy": True,
    }


def test_create_wt_layout_returns_generator_script_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeGenerator:
        def __init__(
            self,
            layout_config: LayoutConfig,
            session_name: str,
            exit_mode: str,
        ) -> None:
            assert layout_config == _layout()
            assert session_name == "demo"
            assert exit_mode == "backToShell"
            self.script_path: str | None = "/tmp/demo.ps1"

        def create_layout_file(self) -> bool:
            return True

    monkeypatch.setattr(wt_local, "WTLayoutGenerator", FakeGenerator)

    result = wt_local.create_wt_layout(
        layout_config=_layout(),
        output_path="ignored",
        exit_mode="backToShell",
    )

    assert result == "/tmp/demo.ps1"


def test_run_wt_layout_raises_on_subprocess_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_generate_random_suffix(_length: int) -> str:
        return "deadbeef"

    def fake_generate_wt_command_string(
        _layout_config: LayoutConfig,
        _session_name: str,
        _exit_mode: str,
    ) -> str:
        return "wt new-tab --title editor"

    def fake_run(
        args: str,
        shell: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text
        assert shell is True
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="boom",
        )

    monkeypatch.setattr(wt_local, "TMP_LAYOUT_DIR", tmp_path)
    monkeypatch.setattr(
        wt_local,
        "generate_random_suffix",
        fake_generate_random_suffix,
    )
    monkeypatch.setattr(
        wt_local,
        "generate_wt_command_string",
        fake_generate_wt_command_string,
    )
    monkeypatch.setattr(wt_local.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="boom"):
        wt_local.run_wt_layout(_layout(), exit_mode="backToShell")


def test_run_command_in_wt_tab_formats_optional_cwd() -> None:
    with_cwd = wt_local.run_command_in_wt_tab(
        command="python app.py",
        tab_name="editor",
        cwd="/work/app",
    )
    without_cwd = wt_local.run_command_in_wt_tab(
        command="python app.py",
        tab_name="editor",
        cwd=None,
    )

    assert '-d "/work/app"' in with_cwd
    assert 'wt new-tab --title "editor"  "python app.py"' in without_cwd
