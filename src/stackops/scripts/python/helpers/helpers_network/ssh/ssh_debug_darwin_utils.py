import os
import shutil
from pathlib import Path

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import run_argv
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


def find_darwin_sshd() -> Path | None:
    candidates = (
        Path("/usr/sbin/sshd"),
        Path("/usr/local/sbin/sshd"),
        Path("/opt/homebrew/sbin/sshd"),
    )
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    discovered = shutil.which("sshd")
    if discovered is not None:
        path = Path(discovered)
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def check_remote_login_service() -> SSHDebugCheck:
    completed = run_argv(("/usr/sbin/systemsetup", "-getremotelogin"))
    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or completed.failure or "unknown command failure"
        return SSHDebugCheck(
            identifier="ssh_service",
            group="service",
            label="Remote Login service",
            status="unknown",
            message=f"Remote Login state could not be read without elevation: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect Remote Login in System Settings; this diagnostic will not request administrator access.",),
        )
    state_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip().startswith("Remote Login:")]
    if state_lines == ["Remote Login: On"]:
        return SSHDebugCheck(
            identifier="ssh_service",
            group="service",
            label="Remote Login service",
            status="ok",
            message="systemsetup reports Remote Login: On",
            command_suggestions=(),
            manual_advice=(),
        )
    if state_lines == ["Remote Login: Off"]:
        return SSHDebugCheck(
            identifier="ssh_service",
            group="service",
            label="Remote Login service",
            status="error",
            message="systemsetup reports Remote Login: Off",
            command_suggestions=("sudo systemsetup -setremotelogin on",),
            manual_advice=("Enable Remote Login only for the users who should receive SSH access.",),
        )
    return SSHDebugCheck(
        identifier="ssh_service",
        group="service",
        label="Remote Login service",
        status="unknown",
        message="systemsetup returned an unrecognized Remote Login state",
        command_suggestions=(),
        manual_advice=("Inspect Remote Login in System Settings.",),
    )

