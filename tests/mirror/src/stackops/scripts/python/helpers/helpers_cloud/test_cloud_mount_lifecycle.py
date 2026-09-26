import os
import shlex
import shutil
import signal
import subprocess
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from stackops.scripts.python.helpers.helpers_cloud.cloud_mount_tmux import build_mount_pane_command


@dataclass(frozen=True)
class LifecycleServer:
    directory: Path
    command: list[str]
    environment: dict[str, str]


def _tmux(server: LifecycleServer, arguments: list[str]) -> str:
    result = subprocess.run(
        [*server.command, *arguments], cwd=server.directory, env=server.environment, capture_output=True, text=True, timeout=10, check=True
    )
    return result.stdout.strip()


def _wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 10
    while not condition():
        assert time.monotonic() < deadline, "Mount lifecycle did not finish within 10 seconds"
        time.sleep(0.02)


def _process_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.fixture
def lifecycle_server() -> Iterator[LifecycleServer]:
    tmux_binary = shutil.which("tmux")
    if tmux_binary is None or not Path("/bin/bash").exists():
        pytest.skip("tmux and Bash are required for mount lifecycle tests")
    temporary_root = Path(__file__).resolve().parents[8] / ".ai" / "tmp_scripts" / "rclone_lifecycle"
    temporary_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="regression-", dir=temporary_root) as directory_name:
        directory = Path(directory_name)
        server = LifecycleServer(
            directory=directory,
            command=[tmux_binary, "-S", str(directory / "tmux.sock"), "-f", "/dev/null"],
            environment={"PATH": "/usr/bin:/bin", "SHELL": "/bin/bash", "TERM": "xterm-256color"},
        )
        _tmux(server=server, arguments=["new-session", "-d", "-s", "keeper", "/bin/sleep", "600"])
        try:
            yield server
        finally:
            subprocess.run([*server.command, "kill-server"], cwd=directory, env=server.environment, capture_output=True, timeout=10, check=False)
            pid_file = directory / "child.pid"
            if pid_file.exists():
                pid = int(pid_file.read_text(encoding="utf-8"))
                if _process_exists(pid):
                    os.kill(pid, signal.SIGTERM)
                    _wait_until(lambda: not _process_exists(pid))
            mountpoint = directory / "mount"
            if mountpoint.is_mount():
                subprocess.run(["fusermount3", "-u", str(mountpoint)], cwd=directory, capture_output=True, timeout=10, check=True)


@pytest.mark.parametrize(
    "shutdown_arguments",
    [
        ["kill-pane", "-t", "mount:0.0"],
        ["kill-window", "-t", "mount:0"],
        ["kill-session", "-t", "mount"],
        ["kill-server"],
        ["send-keys", "-t", "mount:0.0", "C-c"],
    ],
    ids=["pane", "window", "session", "server", "ctrl-c"],
)
def test_tmux_shutdown_waits_for_mount_cleanup(lifecycle_server: LifecycleServer, shutdown_arguments: list[str]) -> None:
    server = lifecycle_server
    child_script = server.directory / "mount stand-in.sh"
    child_script.write_text(
        """trap 'touch "$1/hangup"' HUP
trap 'touch "$1/terminating"; sleep 0.3; touch "$1/finished"; exit 0' TERM
printf '%s' "$$" > "$1/child.pid"
while :; do sleep 0.05; done
""",
        encoding="utf-8",
    )
    mount_command = shlex.join(["/bin/bash", "--noprofile", "--norc", str(child_script), str(server.directory)])
    script = shlex.split(build_mount_pane_command(mount_command=mount_command))[2]
    wrapper_pid = int(
        _tmux(
            server=server,
            arguments=["new-session", "-d", "-P", "-F", "#{pane_pid}", "-s", "mount", "/bin/bash", "--noprofile", "--norc", "-c", script],
        )
    )
    pid_file = server.directory / "child.pid"
    _wait_until(pid_file.exists)
    child_pid = int(pid_file.read_text(encoding="utf-8"))
    os.kill(child_pid, signal.SIGHUP)
    _wait_until((server.directory / "hangup").exists)
    assert _process_exists(child_pid)

    _tmux(server=server, arguments=shutdown_arguments)

    _wait_until((server.directory / "terminating").exists)
    assert _process_exists(wrapper_pid), "The wrapper exited before the mount finished cleaning up"
    _wait_until((server.directory / "finished").exists)
    _wait_until(lambda: not _process_exists(child_pid))
    _wait_until(lambda: not _process_exists(wrapper_pid))


@pytest.mark.parametrize("exit_code", [0, 27])
def test_mount_exit_status_is_preserved(lifecycle_server: LifecycleServer, exit_code: int) -> None:
    mount_command = shlex.join(["/bin/sh", "-c", f"""exit {exit_code}"""])
    script = shlex.split(build_mount_pane_command(mount_command=mount_command))[2]
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-c", script],
        cwd=lifecycle_server.directory,
        env=lifecycle_server.environment,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == exit_code


def test_mount_preserves_standard_input(lifecycle_server: LifecycleServer) -> None:
    script = shlex.split(build_mount_pane_command(mount_command="/bin/cat"))[2]
    result = subprocess.run(
        ["/bin/bash", "--noprofile", "--norc", "-c", script],
        cwd=lifecycle_server.directory,
        env=lifecycle_server.environment,
        input="interactive mount input",
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert result.stdout == "interactive mount input"


def test_killing_session_unmounts_local_rclone(lifecycle_server: LifecycleServer) -> None:
    rclone_binary = shutil.which("rclone")
    if rclone_binary is None or shutil.which("fusermount3") is None or not os.access("/dev/fuse", os.R_OK | os.W_OK):
        pytest.skip("rclone, fusermount3 and an accessible FUSE device are required")
    server = lifecycle_server
    source = server.directory / "source"
    mountpoint = server.directory / "mount"
    source.mkdir()
    mountpoint.mkdir()
    (source / "example.txt").write_text("local mount verification", encoding="utf-8")
    mount_command = shlex.join(
        [
            rclone_binary,
            "mount",
            f""":local:{source}""",
            str(mountpoint),
            "--config",
            "/dev/null",
            "--cache-dir",
            str(server.directory / "cache"),
            "--vfs-cache-mode",
            "full",
            "--log-file",
            str(server.directory / "rclone.log"),
        ]
    )
    child_script = f"""printf '%s' "$$" > {shlex.quote(str(server.directory / "child.pid"))}; exec {mount_command}"""
    script = shlex.split(build_mount_pane_command(mount_command=shlex.join(["/bin/sh", "-c", child_script])))[2]
    _tmux(server=server, arguments=["new-session", "-d", "-s", "mount", "/bin/bash", "--noprofile", "--norc", "-c", script])
    _wait_until(mountpoint.is_mount)
    assert (mountpoint / "example.txt").read_text(encoding="utf-8") == "local mount verification"
    child_pid = int((server.directory / "child.pid").read_text(encoding="utf-8"))
    _tmux(server=server, arguments=["split-window", "-d", "-t", "mount:0", "-c", str(mountpoint), "/bin/sleep", "600"])

    _tmux(server=server, arguments=["kill-session", "-t", "mount"])

    _wait_until(lambda: not mountpoint.is_mount())
    _wait_until(lambda: not _process_exists(child_pid))
