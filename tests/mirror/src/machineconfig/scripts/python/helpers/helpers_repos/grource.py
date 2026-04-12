from __future__ import annotations

from pathlib import Path

import pytest
import typer

from machineconfig.scripts.python.helpers.helpers_repos import grource as grource_module


def test_get_gource_executable_prefers_existing_windows_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    install_dir = tmp_path / "gource"
    install_dir.mkdir()
    executable = install_dir / "gource.exe"
    executable.write_text("", encoding="utf-8")

    monkeypatch.setattr(grource_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(grource_module, "get_gource_install_dir", lambda: install_dir)

    assert grource_module.get_gource_executable() == executable


def test_install_gource_windows_rejects_non_windows_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grource_module.platform, "system", lambda: "Linux")

    with pytest.raises(OSError, match="Windows only"):
        grource_module.install_gource_windows()


def test_visualize_rejects_missing_repository(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(grource_module.platform, "system", lambda: "Linux")
    missing_repo = tmp_path / "missing"

    with pytest.raises(typer.Exit) as exc_info:
        grource_module.visualize(repo=str(missing_repo))

    assert exc_info.value.exit_code == 1


def test_visualize_builds_interactive_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_path = tmp_path / "demo"
    repo_path.joinpath(".git").mkdir(parents=True)
    gource_executable = tmp_path / "bin" / "gource"
    gource_executable.parent.mkdir(parents=True)
    gource_executable.write_text("", encoding="utf-8")

    commands: list[list[str]] = []

    def fake_run(command: list[str], check: bool) -> None:
        _ = check
        commands.append(command)

    monkeypatch.setattr(grource_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(grource_module, "get_gource_executable", lambda: gource_executable)
    monkeypatch.setattr(grource_module.subprocess, "run", fake_run)

    grource_module.visualize(
        repo=str(repo_path),
        resolution="1280x720",
        seconds_per_day=0.2,
        auto_skip_seconds=2.0,
        hide_items=["date"],
        key_items=True,
        fullscreen=True,
        viewport="1000x800",
        max_files=5,
        file_idle_time=2,
        background_color="abcdef",
        font_size=18,
        camera_mode="track",
    )

    command = commands[0]
    assert command[0] == str(gource_executable)
    assert str(repo_path) in command
    assert "--hide" in command
    assert "--key" in command
    assert "--fullscreen" in command
    assert "--viewport" in command
    assert "--max-files" in command
    assert "--file-idle-time" in command
    assert "--background-colour" in command
    assert "--title" in command
    assert repo_path.name in command


def test_install_exits_outside_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grource_module.platform, "system", lambda: "Linux")

    with pytest.raises(typer.Exit) as exc_info:
        grource_module.install()

    assert exc_info.value.exit_code == 1
