from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_cloud import cloud_copy
from machineconfig.scripts.python.helpers.helpers_cloud import helpers2
from machineconfig.utils.io import GpgCommandError
from machineconfig.utils.rclone import RcloneCommandError


def test_cloud_copy_download_prints_gpg_failure_and_exits(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def fake_parse_cloud_source_target(**_: object) -> tuple[str, str, str]:
        return "demo", "demo:archive/plain.gpg", str(tmp_path.joinpath("plain.txt"))

    def fake_from_cloud(*, local_path: Path, cloud: str, remote_path: Path, transfers: int, verbose: bool) -> Path:
        _ = cloud, remote_path, transfers, verbose
        return local_path

    def fake_decrypt_file_asymmetric(file_path: Path) -> Path:
        raise GpgCommandError(
            command=["gpg", "--batch", "--yes", "--decrypt", "--output", str(file_path.with_suffix("")), str(file_path)],
            returncode=2,
            stdout="",
            stderr="gpg: decryption failed: No secret key\n",
            hint="No matching private key is available in the current GPG keyring.",
        )

    monkeypatch.setattr(helpers2, "parse_cloud_source_target", fake_parse_cloud_source_target)
    monkeypatch.setattr(cloud_copy.rclone_wrapper, "from_cloud", fake_from_cloud)
    monkeypatch.setattr(cloud_copy, "decrypt_file_asymmetric", fake_decrypt_file_asymmetric)
    monkeypatch.setattr(
        cloud_copy,
        "decrypt_file_symmetric",
        lambda file_path, pwd: pytest.fail("decrypt_file_symmetric should not be used"),
    )

    with pytest.raises(SystemExit) as exc_info:
        cloud_copy.main(
            source="demo:archive/plain.gpg",
            target=str(tmp_path.joinpath("plain.txt")),
            overwrite=False,
            share=False,
            rel2home=False,
            root="myhome",
            key=None,
            pwd=None,
            encrypt=True,
            zip_=False,
            os_specific=False,
            config=None,
        )

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "GPG command failed." in captured.out
    assert "Command: gpg --batch --yes --decrypt --output" in captured.out
    assert "gpg: decryption failed: No secret key" in captured.out


def test_cloud_copy_download_prints_rclone_failure_and_exits(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    def fake_parse_cloud_source_target(**_: object) -> tuple[str, str, str]:
        return "demo", "demo:archive/plain.gpg", str(tmp_path.joinpath("plain.txt"))

    def fake_from_cloud(*, local_path: Path, cloud: str, remote_path: Path, transfers: int, verbose: bool) -> Path:
        raise RcloneCommandError(
            command=["rclone", "copyto", f"{cloud}:{remote_path.as_posix()}", str(local_path), "--transfers=10"],
            returncode=3,
            stdout="",
            stderr="Failed to copy: object not found\n",
            hint="The requested remote path does not exist.",
        )

    monkeypatch.setattr(helpers2, "parse_cloud_source_target", fake_parse_cloud_source_target)
    monkeypatch.setattr(cloud_copy.rclone_wrapper, "from_cloud", fake_from_cloud)

    with pytest.raises(SystemExit) as exc_info:
        cloud_copy.main(
            source="demo:archive/plain.gpg",
            target=str(tmp_path.joinpath("plain.txt")),
            overwrite=False,
            share=False,
            rel2home=False,
            root="myhome",
            key=None,
            pwd=None,
            encrypt=True,
            zip_=False,
            os_specific=False,
            config=None,
        )

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Rclone command failed." in captured.out
    assert "Command: rclone copyto demo:archive/plain.gpg" in captured.out
    assert "Failed to copy: object not found" in captured.out
    assert "The requested remote path does not exist." in captured.out
