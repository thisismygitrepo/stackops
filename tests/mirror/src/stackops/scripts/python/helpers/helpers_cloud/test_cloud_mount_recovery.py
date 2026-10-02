import errno
import os
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from stackops.scripts.python.helpers.helpers_cloud.cloud_mount_directory import prepare_unix_mount_directory


@pytest.mark.skipif(sys.platform != "linux", reason="Disconnected FUSE recovery uses Linux fusermount3")
def test_prepare_mount_directory_detaches_disconnected_rclone() -> None:
    rclone_binary = shutil.which("rclone")
    if rclone_binary is None or shutil.which("fusermount3") is None or not os.access("/dev/fuse", os.R_OK | os.W_OK):
        pytest.skip("rclone, fusermount3 and an accessible FUSE device are required")
    temporary_root = Path(__file__).resolve().parents[8] / ".ai" / "tmp_scripts" / "cloud_mount_recovery"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="regression-", dir=temporary_root) as directory_name:
        directory = Path(directory_name)
        source = directory / "source"
        mountpoint = directory / "mount"
        source.mkdir()
        mountpoint.mkdir()
        (source / "example.txt").write_text("disconnected mount verification", encoding="utf-8")
        process = subprocess.Popen(
            [
                rclone_binary,
                "mount",
                f""":local:{source}""",
                str(mountpoint),
                "--config",
                "/dev/null",
                "--cache-dir",
                str(directory / "cache"),
                "--log-file",
                str(directory / "rclone.log"),
                "--attr-timeout",
                "0s",
            ],
            cwd=directory,
            env={"PATH": "/usr/bin:/bin"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 10
            while not mountpoint.is_mount():
                assert time.monotonic() < deadline, "Local rclone did not mount within 10 seconds"
                time.sleep(0.02)
            assert (mountpoint / "example.txt").read_text(encoding="utf-8") == "disconnected mount verification"
            process.kill()
            assert process.wait(timeout=10) == -signal.SIGKILL
            with pytest.raises(OSError) as disconnected_error:
                mountpoint.stat()
            assert disconnected_error.value.errno == errno.ENOTCONN

            assert prepare_unix_mount_directory(mount_path=mountpoint, system_name="Linux")

            assert stat.S_ISDIR(mountpoint.stat().st_mode)
            assert not mountpoint.is_mount()
            assert not prepare_unix_mount_directory(mount_path=mountpoint, system_name="Linux")
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            subprocess.run(["fusermount3", "-uz", str(mountpoint)], cwd=directory, capture_output=True, timeout=10, check=False)
