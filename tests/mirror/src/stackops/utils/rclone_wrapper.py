from __future__ import annotations

from pathlib import Path

import pytest

from stackops.utils import rclone_wrapper as rclone_wrapper_module


def test_get_remote_path_relativizes_to_home_and_adds_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rclone_wrapper_module.platform, "system", lambda: "Linux")

    local_path = Path.home() / "projects" / "demo.txt"

    remote_path = rclone_wrapper_module.get_remote_path(local_path=local_path, root="backups", os_specific=True, rel2home=True, strict=True)

    assert remote_path == Path("backups/linux/projects/demo.txt")


def test_get_remote_path_keeps_absolute_source_when_not_under_home() -> None:
    local_path = Path("/tmp") / "outside-home.txt"

    remote_path = rclone_wrapper_module.get_remote_path(local_path=local_path, root=None, os_specific=False, rel2home=True, strict=False)

    assert remote_path == Path("generic_os/tmp/outside-home.txt")


def test_get_remote_path_raises_when_strict_home_relative_fails(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        rclone_wrapper_module.get_remote_path(local_path=tmp_path / "outside-home.txt", root="root", os_specific=False, rel2home=True, strict=True)


def test_to_cloud_uploads_and_returns_share_link(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed_copy: list[tuple[str, str, int, bool, bool]] = []
    observed_link: list[tuple[str, bool]] = []

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        observed_copy.append((in_path, out_path, transfers, show_command, show_progress))

    def fake_link(*, target: str, show_command: bool) -> str:
        observed_link.append((target, show_command))
        return "https://example.test/shared"

    monkeypatch.setattr(rclone_wrapper_module.rclone_utils, "copyto", fake_copyto)
    monkeypatch.setattr(rclone_wrapper_module.rclone_utils, "link", fake_link)

    local_path = tmp_path / "artifact.bin"
    result = rclone_wrapper_module.to_cloud(
        local_path=local_path, cloud="cloudbox", remote_path=Path("bucket/artifact.bin"), share=True, verbose=True, transfers=7
    )

    assert result == "https://example.test/shared"
    assert observed_copy == [(local_path.absolute().as_posix(), "cloudbox:bucket/artifact.bin", 7, True, True)]
    assert observed_link == [("cloudbox:bucket/artifact.bin", True)]


def test_from_cloud_creates_parent_and_downloads(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: list[tuple[str, str, int, bool, bool]] = []

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        observed.append((in_path, out_path, transfers, show_command, show_progress))

    monkeypatch.setattr(rclone_wrapper_module.rclone_utils, "copyto", fake_copyto)

    local_path = tmp_path / "downloads" / "artifact.bin"
    result = rclone_wrapper_module.from_cloud(
        local_path=local_path, cloud="cloudbox", remote_path=Path("bucket/artifact.bin"), transfers=3, verbose=False
    )

    assert result == local_path.absolute()
    assert local_path.parent.is_dir()
    assert observed == [("cloudbox:bucket/artifact.bin", local_path.absolute().as_posix(), 3, False, False)]


def test_sync_to_cloud_uses_bisync_for_bidirectional_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed_bisync: list[tuple[str, str, int, bool, bool, bool]] = []
    observed_sync: list[tuple[str, str, int, bool, bool, bool]] = []

    def fake_bisync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
        observed_bisync.append((source, target, transfers, delete_during, show_command, show_progress))

    def fake_sync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
        observed_sync.append((source, target, transfers, delete_during, show_command, show_progress))

    monkeypatch.setattr(rclone_wrapper_module.rclone_utils, "bisync", fake_bisync)
    monkeypatch.setattr(rclone_wrapper_module.rclone_utils, "sync", fake_sync)

    local_path = tmp_path / "sync" / "notes"
    result = rclone_wrapper_module.sync_to_cloud(
        local_path=local_path,
        cloud="cloudbox",
        remote_path=Path("mirror/notes"),
        sync_up=False,
        sync_down=False,
        transfers=5,
        delete=True,
        verbose=True,
    )

    assert result == local_path.absolute()
    assert observed_bisync == [("cloudbox:mirror/notes", local_path.absolute().as_posix(), 5, True, True, True)]
    assert observed_sync == []


def test_sync_to_cloud_uses_sync_for_upload_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed_sync: list[tuple[str, str, int, bool, bool, bool]] = []

    def fake_sync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
        observed_sync.append((source, target, transfers, delete_during, show_command, show_progress))

    monkeypatch.setattr(rclone_wrapper_module.rclone_utils, "sync", fake_sync)

    local_path = tmp_path / "sync" / "notes"
    rclone_wrapper_module.sync_to_cloud(
        local_path=local_path,
        cloud="cloudbox",
        remote_path=Path("mirror/notes"),
        sync_up=True,
        sync_down=False,
        transfers=9,
        delete=False,
        verbose=False,
    )

    assert observed_sync == [(local_path.absolute().as_posix(), "cloudbox:mirror/notes", 9, False, False, False)]
