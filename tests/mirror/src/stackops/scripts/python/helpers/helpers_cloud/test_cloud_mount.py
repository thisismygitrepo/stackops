import platform
import shlex
import subprocess
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.cloud import get_app
from stackops.scripts.python.helpers.helpers_cloud import cloud_mount, cloud_mount_tmux
from stackops.utils.options_utils import options


@dataclass(frozen=True)
class MountDependencies:
    run: MagicMock
    tmux: MagicMock
    choose: MagicMock


@pytest.fixture
def mount_dependencies(monkeypatch: pytest.MonkeyPatch) -> MountDependencies:
    config = ConfigParser()
    config.read_dict({"odOracle": {"type": "onedrive"}, "team's drive": {"type": "drive"}})
    dependencies = MountDependencies(
        run=MagicMock(spec=subprocess.run),
        tmux=MagicMock(return_value="tmux attach"),
        choose=MagicMock(return_value=["odOracle", "team's drive"]),
    )
    monkeypatch.setattr(cloud_mount, "get_rclone_config", MagicMock(return_value=config))
    monkeypatch.setattr(cloud_mount_tmux, "build_tmux_launch_command", dependencies.tmux)
    monkeypatch.setattr(subprocess, "run", dependencies.run)
    monkeypatch.setattr(Path, "mkdir", MagicMock())
    monkeypatch.setattr(platform, "system", MagicMock(return_value="Linux"))
    monkeypatch.setattr(options, "choose_from_options", dependencies.choose)
    return dependencies


@pytest.mark.parametrize("flag", ["--daemon", "-D"])
@pytest.mark.parametrize("system_name", ["Linux", "Darwin"])
def test_daemon_mounts_preserve_arguments_and_skip_tmux(
    mount_dependencies: MountDependencies, monkeypatch: pytest.MonkeyPatch, flag: str, system_name: str
) -> None:
    monkeypatch.setattr(platform, "system", MagicMock(return_value=system_name))
    destination = "/mounts/team's data $(touch surprise)"

    result = CliRunner().invoke(get_app(), ["mount", "odOracle,team's drive", flag, "-d", destination])

    assert result.exit_code == 0, result.output
    assert "running in the background" in result.output
    assert mount_dependencies.run.call_args_list == [
        call(
            [
                "rclone", "mount", f"""{remote}:""", str(Path(destination) / remote),
                "--vfs-cache-mode", "full", "--file-perms=0777", "--daemon",
            ],
            shell=False,
            check=True,
        )
        for remote in ("odOracle", "team's drive")
    ]
    mount_dependencies.tmux.assert_not_called()
    mount_dependencies.choose.assert_not_called()


def test_mount_uses_tmux_by_default_and_quotes_shell_arguments(mount_dependencies: MountDependencies) -> None:
    destination = "/mounts/team's data $(touch surprise)"

    result = CliRunner().invoke(get_app(), ["mount", "team's drive", "--destination", destination])

    assert result.exit_code == 0, result.output
    mount_dependencies.tmux.assert_called_once_with(
        mount_commands={
            "team's drive": shlex.join([
                "rclone", "mount", "team's drive:", destination, "--vfs-cache-mode", "full", "--file-perms=0777",
            ])
        },
        mount_locations={"team's drive": destination},
        session_name="cloud-mount",
    )
    mount_dependencies.run.assert_called_once_with("tmux attach", shell=True, check=True)


def test_daemon_mounts_interactive_selection(mount_dependencies: MountDependencies) -> None:
    result = CliRunner().invoke(get_app(), ["mount", "--daemon", "--destination", "/mounts"])

    assert result.exit_code == 0, result.output
    assert mount_dependencies.run.call_count == 2
    mount_dependencies.choose.assert_called_once()
    mount_dependencies.tmux.assert_not_called()


def test_windows_rejects_daemon_before_starting_mounts(
    mount_dependencies: MountDependencies, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(platform, "system", MagicMock(return_value="Windows"))

    result = CliRunner().invoke(get_app(), ["mount", "odOracle", "--daemon", "--destination", "X:"])

    assert result.exit_code == 1
    assert "--daemon is only supported on Linux/macOS" in result.output
    mount_dependencies.run.assert_not_called()
    mount_dependencies.tmux.assert_not_called()


@pytest.mark.parametrize(
    ("failure", "expected_exit"),
    [(subprocess.CalledProcessError(returncode=7, cmd="rclone"), 7), (FileNotFoundError("rclone missing"), 1)],
)
def test_daemon_failure_exits_without_success_message(
    mount_dependencies: MountDependencies, failure: OSError | subprocess.CalledProcessError, expected_exit: int
) -> None:
    mount_dependencies.run.side_effect = failure

    result = CliRunner().invoke(get_app(), ["mount", "odOracle", "--daemon", "--destination", "/mounts"])

    assert result.exit_code == expected_exit, result.output
    assert "rclone" in result.output
    assert "completed successfully" not in result.output
    mount_dependencies.run.assert_called_once()
    mount_dependencies.tmux.assert_not_called()
