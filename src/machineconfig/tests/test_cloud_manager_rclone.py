from collections.abc import Callable
from pathlib import Path

import pytest

import machineconfig.cluster.remote.cloud_manager as cloud_manager_module


_SYNC_FROM_CLOUD: Callable[[str, Path], None] = getattr(cloud_manager_module, "_sync_from_cloud")
_SYNC_TO_CLOUD: Callable[[str, Path], None] = getattr(cloud_manager_module, "_sync_to_cloud")
_SYNC_DIR_FROM_CLOUD: Callable[[str, Path], None] = getattr(cloud_manager_module, "_sync_dir_from_cloud")
_SYNC_DIR_TO_CLOUD: Callable[[str, Path], None] = getattr(cloud_manager_module, "_sync_dir_to_cloud")


def _missing_remote_path_error() -> cloud_manager_module.rclone_utils.RcloneCommandError:
    return cloud_manager_module.rclone_utils.RcloneCommandError(
        command=["rclone", "copyto", "demo:missing", "local.txt", "--transfers=10"],
        returncode=3,
        stdout="",
        stderr="Failed to copy: object not found\n",
        hint="The requested remote path does not exist.",
    )


def _config_error() -> cloud_manager_module.rclone_utils.RcloneCommandError:
    return cloud_manager_module.rclone_utils.RcloneCommandError(
        command=["rclone", "copyto", "demo:missing", "local.txt", "--transfers=10"],
        returncode=3,
        stdout="",
        stderr="didn't find section in config file\n",
        hint="The configured rclone remote could not be resolved. Verify the remote name and your rclone config.",
    )


def test_sync_from_cloud_uses_shared_rclone_copyto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path.joinpath("lock.txt")
    calls: list[tuple[str, str, int, bool, bool]] = []

    monkeypatch.setattr(cloud_manager_module, "_rel2home", lambda _path: "tmp_results/remote_machines/cloud/lock.txt")

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        calls.append((in_path, out_path, transfers, show_command, show_progress))

    monkeypatch.setattr(cloud_manager_module.rclone_utils, "copyto", fake_copyto)

    _SYNC_FROM_CLOUD("demo", target)

    assert calls == [
        ("demo:tmp_results/remote_machines/cloud/lock.txt", str(target), 10, False, False),
    ]


def test_sync_from_cloud_ignores_missing_remote_path_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path.joinpath("lock.txt")

    monkeypatch.setattr(cloud_manager_module, "_rel2home", lambda _path: "tmp_results/remote_machines/cloud/lock.txt")

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        raise _missing_remote_path_error()

    monkeypatch.setattr(cloud_manager_module.rclone_utils, "copyto", fake_copyto)

    _SYNC_FROM_CLOUD("demo", target)


def test_sync_from_cloud_surfaces_non_missing_remote_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path.joinpath("lock.txt")

    monkeypatch.setattr(cloud_manager_module, "_rel2home", lambda _path: "tmp_results/remote_machines/cloud/lock.txt")

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        raise _config_error()

    monkeypatch.setattr(cloud_manager_module.rclone_utils, "copyto", fake_copyto)

    with pytest.raises(cloud_manager_module.rclone_utils.RcloneCommandError):
        _SYNC_FROM_CLOUD("demo", target)


def test_sync_to_cloud_uses_shared_rclone_copyto(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("lock.txt")
    source.write_text("owner", encoding="utf-8")
    calls: list[tuple[str, str, int, bool, bool]] = []

    monkeypatch.setattr(cloud_manager_module, "_rel2home", lambda _path: "tmp_results/remote_machines/cloud/lock.txt")

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        calls.append((in_path, out_path, transfers, show_command, show_progress))

    monkeypatch.setattr(cloud_manager_module.rclone_utils, "copyto", fake_copyto)

    _SYNC_TO_CLOUD("demo", source)

    assert calls == [
        (str(source), "demo:tmp_results/remote_machines/cloud/lock.txt", 10, False, False),
    ]


def test_sync_dir_from_cloud_uses_shared_rclone_sync_and_ignores_missing_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path.joinpath("cloud")
    calls: list[tuple[str, str, int, bool, bool, bool]] = []

    monkeypatch.setattr(cloud_manager_module, "_rel2home", lambda _path: "tmp_results/remote_machines/cloud")

    def fake_sync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
        calls.append((source, target, transfers, delete_during, show_command, show_progress))
        raise _missing_remote_path_error()

    monkeypatch.setattr(cloud_manager_module.rclone_utils, "sync", fake_sync)

    _SYNC_DIR_FROM_CLOUD("demo", directory)

    assert calls == [
        ("demo:tmp_results/remote_machines/cloud", str(directory), 10, False, False, False),
    ]


def test_sync_dir_to_cloud_uses_shared_rclone_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path.joinpath("cloud")
    directory.mkdir()
    calls: list[tuple[str, str, int, bool, bool, bool]] = []

    monkeypatch.setattr(cloud_manager_module, "_rel2home", lambda _path: "tmp_results/remote_machines/cloud")

    def fake_sync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
        calls.append((source, target, transfers, delete_during, show_command, show_progress))

    monkeypatch.setattr(cloud_manager_module.rclone_utils, "sync", fake_sync)

    _SYNC_DIR_TO_CLOUD("demo", directory)

    assert calls == [
        (str(directory), "demo:tmp_results/remote_machines/cloud", 10, False, False, False),
    ]