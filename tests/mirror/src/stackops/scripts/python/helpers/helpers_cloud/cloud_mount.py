

import configparser
import platform
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from stackops.scripts.python.helpers.helpers_cloud import cloud_mont_tmux
from stackops.scripts.python.helpers.helpers_cloud import cloud_mount
from stackops.utils import accessories as accessories_module
from stackops.utils import io as io_module
from stackops.utils import path_extended as path_extended_module


@pytest.mark.parametrize(
    ("system_name", "expected_relative_path"), [("Linux", ".config/rclone/rclone.conf"), ("Windows", "AppData/Roaming/rclone/rclone.conf")]
)
def test_get_rclone_config_reads_platform_specific_path(
    system_name: str, expected_relative_path: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured_paths: list[Path] = []

    def fake_read_ini(path: Path) -> dict[str, str]:
        captured_paths.append(path)
        return {"path": path.as_posix()}

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(platform, "system", lambda: system_name)
    monkeypatch.setattr(io_module, "read_ini", fake_read_ini)

    result = cloud_mount.get_rclone_config()

    assert result == {"path": tmp_path.joinpath(expected_relative_path).as_posix()}
    assert captured_paths == [tmp_path.joinpath(expected_relative_path)]


def test_get_mprocs_mount_txt_writes_windows_side_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    monkeypatch.setattr(path_extended_module, "PathExtended", Path)
    monkeypatch.setattr(accessories_module, "randstr", lambda: "fixed-name")

    command = cloud_mount.get_mprocs_mount_txt(cloud="mycloud", rclone_cmd="rclone mount mycloud:", cloud_brand="drive")

    script_path = tmp_path.joinpath("tmp_results", "tmp_files", "fixed-name.ps1")
    assert script_path.is_file()
    assert "rclone about mycloud:" in script_path.read_text(encoding="utf-8")
    assert "powershell" in command


def test_mount_linux_tmux_builds_command_and_runs_subprocess(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = configparser.ConfigParser()
    config.add_section("drive")
    destination = tmp_path.joinpath("mounted-drive")
    subprocess_calls: list[tuple[str, bool, bool]] = []
    builder_calls: list[tuple[dict[str, str], dict[str, str], str]] = []

    def fake_build_tmux_launch_command(mount_commands: dict[str, str], mount_locations: dict[str, str], session_name: str) -> str:
        builder_calls.append((mount_commands, mount_locations, session_name))
        return "TMUX_CMD"

    def fake_subprocess_run(command: str, *, shell: bool, check: bool) -> CompletedProcess[str]:
        subprocess_calls.append((command, shell, check))
        return CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(cloud_mount, "get_rclone_config", lambda: config)
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(cloud_mont_tmux, "build_tmux_launch_command", fake_build_tmux_launch_command)
    monkeypatch.setattr("subprocess.run", fake_subprocess_run)

    cloud_mount.mount(cloud="drive", destination=str(destination), network=None, zellij_session="session-one", backend="tmux", interactive=False)

    assert destination.is_dir()
    assert builder_calls == [
        ({"drive": f"rclone mount drive: {destination} --vfs-cache-mode full --file-perms=0777"}, {"drive": str(destination)}, "session-one")
    ]
    assert subprocess_calls == [("TMUX_CMD", True, True)]


def test_get_app_registers_mount_command() -> None:
    app = cloud_mount.get_app()

    assert app.registered_commands
    assert app.registered_commands[0].name == "mount"
    assert app.registered_commands[0].callback is cloud_mount.mount
