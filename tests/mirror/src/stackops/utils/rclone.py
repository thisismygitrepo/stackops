from __future__ import annotations

from collections.abc import Callable
import subprocess
from typing import cast

import pytest

from stackops.utils import rclone as rclone_module


def test_rclone_hint_distinguishes_config_errors_from_missing_paths() -> None:
    hint_func = cast(Callable[[str, str], str | None], getattr(rclone_module, "_rclone_hint"))

    config_hint = hint_func("", "directory not found because it didn't find section in config file")
    assert config_hint == ("The configured rclone remote could not be resolved. Verify the remote name and your rclone config.")

    missing_hint = hint_func("file not found", "")
    assert missing_hint == "The requested remote path does not exist."


def test_is_missing_remote_path_error_uses_combined_output() -> None:
    error = rclone_module.RcloneCommandError(command=["rclone", "ls", "remote:path"], returncode=3, stdout="file not found", stderr="", hint=None)

    assert rclone_module.is_missing_remote_path_error(error) is True


def test_copy_sync_and_bisync_build_expected_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: list[tuple[list[str], bool, bool]] = []

    def fake_run(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
        observed.append((command, show_command, show_progress))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(rclone_module, "_run_rclone", fake_run)

    rclone_module.copyto(in_path="local.txt", out_path="remote:file.txt", transfers=4, show_command=True, show_progress=True)
    rclone_module.sync(source="src", target="dst", transfers=2, delete_during=True, show_command=False, show_progress=False)
    rclone_module.bisync(source="left", target="right", transfers=8, delete_during=False, show_command=True, show_progress=True)

    assert observed == [
        (["rclone", "copyto", "local.txt", "remote:file.txt", "--transfers=4", "--progress"], True, True),
        (["rclone", "sync", "src", "dst", "--transfers=2", "--verbose", "--delete-during"], False, False),
        (["rclone", "bisync", "left", "right", "--resync", "--remove-empty-dirs", "--transfers=8", "--verbose", "--progress"], True, True),
    ]


def test_link_returns_first_non_empty_line(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
        assert command == ["rclone", "link", "remote:file.txt"]
        assert show_command is False
        assert show_progress is False
        return subprocess.CompletedProcess(command, 0, "\n  https://example.test/share  \nignored\n", "")

    monkeypatch.setattr(rclone_module, "_run_rclone", fake_run)

    assert rclone_module.link(target="remote:file.txt", show_command=False) == "https://example.test/share"


def test_link_raises_when_rclone_returns_no_url(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "\n \n", "")

    monkeypatch.setattr(rclone_module, "_run_rclone", fake_run)

    with pytest.raises(RuntimeError, match="rclone link returned no output"):
        rclone_module.link(target="remote:file.txt", show_command=True)
