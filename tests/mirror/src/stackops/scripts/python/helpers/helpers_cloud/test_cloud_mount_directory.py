import errno
import subprocess
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from stackops.scripts.python.helpers.helpers_cloud.cloud_mount_directory import prepare_unix_mount_directory


@dataclass(frozen=True)
class DirectoryDependencies:
    stat: MagicMock
    mkdir: MagicMock
    run: MagicMock


@pytest.fixture
def directory_dependencies(monkeypatch: pytest.MonkeyPatch) -> DirectoryDependencies:
    dependencies = DirectoryDependencies(stat=MagicMock(), mkdir=MagicMock(), run=MagicMock(spec=subprocess.run))
    monkeypatch.setattr(Path, "stat", dependencies.stat)
    monkeypatch.setattr(Path, "mkdir", dependencies.mkdir)
    monkeypatch.setattr(subprocess, "run", dependencies.run)
    return dependencies


def test_disconnected_linux_mount_is_detached_before_directory_creation(directory_dependencies: DirectoryDependencies) -> None:
    mount_path = Path("/mounts/team's data $(touch surprise)")
    directory_dependencies.stat.side_effect = [OSError(errno.ENOTCONN, "Transport endpoint is not connected"), None]
    calls = MagicMock()
    calls.attach_mock(directory_dependencies.run, "unmount")
    calls.attach_mock(directory_dependencies.mkdir, "mkdir")
    calls.attach_mock(directory_dependencies.stat, "stat")

    recovered = prepare_unix_mount_directory(mount_path=mount_path, system_name="Linux")

    assert recovered
    directory_dependencies.run.assert_called_once_with(["fusermount3", "-uz", str(mount_path)], check=True)
    directory_dependencies.mkdir.assert_called_once_with(parents=True, exist_ok=True)
    assert [call[0] for call in calls.mock_calls] == ["stat", "unmount", "mkdir", "stat"]


@pytest.mark.parametrize("missing", [False, True])
def test_readable_and_missing_directories_do_not_unmount(directory_dependencies: DirectoryDependencies, missing: bool) -> None:
    if missing:
        directory_dependencies.stat.side_effect = [FileNotFoundError(errno.ENOENT, "No such file"), None]

    recovered = prepare_unix_mount_directory(mount_path=Path("/mounts/odo"), system_name="Linux")

    assert not recovered
    directory_dependencies.run.assert_not_called()
    directory_dependencies.mkdir.assert_called_once_with(parents=True, exist_ok=True)


@pytest.mark.parametrize("error_number", [errno.EACCES, errno.EIO])
def test_other_filesystem_errors_propagate(directory_dependencies: DirectoryDependencies, error_number: int) -> None:
    directory_dependencies.stat.side_effect = OSError(error_number, "Filesystem failure")

    with pytest.raises(OSError) as caught:
        prepare_unix_mount_directory(mount_path=Path("/mounts/odo"), system_name="Linux")

    assert caught.value.errno == error_number
    directory_dependencies.run.assert_not_called()
    directory_dependencies.mkdir.assert_not_called()


def test_macos_disconnected_mount_does_not_run_linux_unmount(directory_dependencies: DirectoryDependencies) -> None:
    directory_dependencies.stat.side_effect = OSError(errno.ENOTCONN, "Transport endpoint is not connected")

    with pytest.raises(OSError) as caught:
        prepare_unix_mount_directory(mount_path=Path("/mounts/odo"), system_name="Darwin")

    assert caught.value.errno == errno.ENOTCONN
    directory_dependencies.run.assert_not_called()


def test_failed_unmount_does_not_prepare_directory(directory_dependencies: DirectoryDependencies) -> None:
    directory_dependencies.stat.side_effect = OSError(errno.ENOTCONN, "Transport endpoint is not connected")
    directory_dependencies.run.side_effect = subprocess.CalledProcessError(returncode=7, cmd="fusermount3")

    with pytest.raises(subprocess.CalledProcessError):
        prepare_unix_mount_directory(mount_path=Path("/mounts/odo"), system_name="Linux")

    directory_dependencies.mkdir.assert_not_called()


def test_failed_post_unmount_directory_check_propagates(directory_dependencies: DirectoryDependencies) -> None:
    directory_dependencies.stat.side_effect = [
        OSError(errno.ENOTCONN, "Transport endpoint is not connected"),
        OSError(errno.EACCES, "Permission denied"),
    ]

    with pytest.raises(OSError) as caught:
        prepare_unix_mount_directory(mount_path=Path("/mounts/odo"), system_name="Linux")

    assert caught.value.errno == errno.EACCES
