from pathlib import Path
import subprocess

import pytest

from stackops.utils.cloud import rclone


def test_list_remote_names_from_config_uses_only_requested_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path.joinpath("synthetic-rclone.conf")
    config_path.write_text("synthetic config placeholder\n", encoding="utf-8")
    commands: list[list[str]] = []

    def run_rclone(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
        assert not show_command
        assert not show_progress
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="alpha:\nbeta:\n", stderr="")

    monkeypatch.setattr(rclone, "_run_rclone", run_rclone)

    assert rclone.list_remote_names_from_config(config_path=config_path) == ("alpha", "beta")
    assert commands == [["rclone", "listremotes", "--config", str(config_path)]]


def test_list_remote_names_from_config_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(rclone.RcloneConfigError, match="does not exist"):
        rclone.list_remote_names_from_config(config_path=tmp_path.joinpath("missing.conf"))


def test_rclone_parse_failure_is_classified_as_config_error() -> None:
    stderr = "CRITICAL: Failed to load config file: could not parse line"

    assert rclone._rclone_hint(stdout="", stderr=stderr) == (
        "The configured rclone remote could not be resolved. Verify the remote name and your rclone config."
    )
    error = rclone.RcloneCommandError(command=["rclone", "copyto", "source", "remote:target"], returncode=1, stdout="", stderr=stderr, hint=None)
    assert not rclone.is_missing_remote_path_error(error=error)
