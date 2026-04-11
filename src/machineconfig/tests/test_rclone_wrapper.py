from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_cloud import helpers2
import machineconfig.utils.rclone_wrapper as rclone_wrapper
from machineconfig.utils.ve import read_default_cloud_config


def test_get_remote_path_makes_path_relative_to_home() -> None:
    remote_path = rclone_wrapper.get_remote_path(
        local_path=Path.home().joinpath("plain.txt"),
        root="myhome",
        os_specific=False,
        rel2home=True,
        strict=True,
    )

    assert remote_path == Path("myhome/generic_os/plain.txt")


def test_get_remote_path_keeps_absolute_suffix_when_path_is_outside_home(tmp_path: Path) -> None:
    local_path = tmp_path.joinpath("plain.txt")

    remote_path = rclone_wrapper.get_remote_path(
        local_path=local_path,
        root="myhome",
        os_specific=False,
        rel2home=True,
        strict=False,
    )

    expected_suffix = local_path.as_posix().lstrip("/")
    assert remote_path == Path(f"myhome/generic_os/{expected_suffix}")


def test_to_cloud_uses_passed_remote_path_and_returns_share_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path.joinpath("plain.txt")
    source.write_text("payload", encoding="utf-8")
    upload_calls: list[tuple[str, str, int, bool, bool]] = []
    link_calls: list[tuple[str, bool]] = []

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        upload_calls.append((in_path, out_path, transfers, show_command, show_progress))

    def fake_link(*, target: str, show_command: bool) -> str:
        link_calls.append((target, show_command))
        return "https://example.invalid/share"

    monkeypatch.setattr(rclone_wrapper.rclone_utils, "copyto", fake_copyto)
    monkeypatch.setattr(rclone_wrapper.rclone_utils, "link", fake_link)

    share_url = rclone_wrapper.to_cloud(
        local_path=source,
        cloud="demo",
        remote_path=Path("archive/plain.txt"),
        share=True,
        verbose=False,
        transfers=4,
    )

    assert upload_calls == [(source.as_posix(), "demo:archive/plain.txt", 4, False, False)]
    assert link_calls == [("demo:archive/plain.txt", False)]
    assert share_url == "https://example.invalid/share"


def test_from_cloud_uses_passed_remote_path_and_creates_parent_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path.joinpath("nested/plain.txt")
    download_calls: list[tuple[str, str, int, bool, bool]] = []

    def fake_copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
        download_calls.append((in_path, out_path, transfers, show_command, show_progress))

    monkeypatch.setattr(rclone_wrapper.rclone_utils, "copyto", fake_copyto)

    result = rclone_wrapper.from_cloud(
        local_path=destination,
        cloud="demo",
        remote_path=Path("archive/plain.txt"),
        transfers=6,
        verbose=False,
    )

    assert destination.parent.exists()
    assert download_calls == [("demo:archive/plain.txt", destination.as_posix(), 6, False, False)]
    assert result == destination


def test_sync_to_cloud_uses_bisync_when_direction_is_not_forced(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path.joinpath("plain.txt")
    bisync_calls: list[tuple[str, str, int, bool, bool, bool]] = []

    def fake_bisync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
        bisync_calls.append((source, target, transfers, delete_during, show_command, show_progress))

    monkeypatch.setattr(rclone_wrapper.rclone_utils, "bisync", fake_bisync)
    monkeypatch.setattr(
        rclone_wrapper.rclone_utils,
        "sync",
        lambda **_: pytest.fail("sync should not be used when bisync is requested"),
    )

    result = rclone_wrapper.sync_to_cloud(
        local_path=directory,
        cloud="demo",
        remote_path=Path("archive/plain.txt"),
        sync_up=False,
        sync_down=False,
        transfers=5,
        delete=True,
        verbose=False,
    )

    assert bisync_calls == [("demo:archive/plain.txt", directory.as_posix(), 5, True, False, False)]
    assert result == directory


def test_sync_to_cloud_uses_sync_for_upload_direction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    directory = tmp_path.joinpath("plain.txt")
    sync_calls: list[tuple[str, str, int, bool, bool, bool]] = []

    def fake_sync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
        sync_calls.append((source, target, transfers, delete_during, show_command, show_progress))

    monkeypatch.setattr(rclone_wrapper.rclone_utils, "sync", fake_sync)
    monkeypatch.setattr(
        rclone_wrapper.rclone_utils,
        "bisync",
        lambda **_: pytest.fail("bisync should not be used when a one-way sync is requested"),
    )

    result = rclone_wrapper.sync_to_cloud(
        local_path=directory,
        cloud="demo",
        remote_path=Path("archive/plain.txt"),
        sync_up=True,
        sync_down=False,
        transfers=7,
        delete=False,
        verbose=False,
    )

    assert sync_calls == [(directory.as_posix(), "demo:archive/plain.txt", 7, False, False, False)]
    assert result == directory


def test_parse_cloud_source_target_appends_gpg_suffix_to_remote_source(tmp_path: Path) -> None:
    cloud_config_explicit = read_default_cloud_config()
    cloud_config_explicit["cloud"] = "demo"
    cloud_config_explicit["encrypt"] = True
    cloud_config_explicit["zip"] = True

    cloud, source, target = helpers2.parse_cloud_source_target(
        cloud_config_explicit=cloud_config_explicit,
        cloud_config_defaults=read_default_cloud_config(),
        cloud_config_name=None,
        source="demo:archive/plain",
        target=str(tmp_path),
    )

    assert cloud == "demo"
    assert source == "demo:archive/plain.zip.gpg"
    assert target == str(tmp_path)


def test_parse_cloud_source_target_appends_gpg_suffix_to_remote_target(tmp_path: Path) -> None:
    source = tmp_path.joinpath("plain.txt")
    source.write_text("payload", encoding="utf-8")
    cloud_config_explicit = read_default_cloud_config()
    cloud_config_explicit["cloud"] = "demo"
    cloud_config_explicit["encrypt"] = True
    cloud_config_explicit["zip"] = True

    cloud, source_value, target = helpers2.parse_cloud_source_target(
        cloud_config_explicit=cloud_config_explicit,
        cloud_config_defaults=read_default_cloud_config(),
        cloud_config_name=None,
        source=str(source),
        target="demo:archive/plain",
    )

    assert cloud == "demo"
    assert source_value == str(source)
    assert target == "demo:archive/plain.zip.gpg"
