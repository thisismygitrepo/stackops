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


def check_remote_login_access(user_name: str) -> SSHDebugCheck:
    group_name = "com.apple.access_ssh"
    group = run_argv(("/usr/bin/dscl", ".", "-read", f"/Groups/{group_name}"))
    if group.returncode != 0:
        detail = group.stderr or group.stdout or group.failure or "unknown directory-service failure"
        if "eDSRecordNotFound" in detail or "-14136" in detail:
            return SSHDebugCheck(
                identifier="remote_login_access",
                group="permissions",
                label="Remote Login user access",
                status="ok",
                message=f"No {group_name} restriction group exists; Remote Login is not user-list restricted",
                command_suggestions=(),
                manual_advice=(),
            )
        return SSHDebugCheck(
            identifier="remote_login_access",
            group="permissions",
            label="Remote Login user access",
            status="unknown",
            message=f"The Remote Login service ACL could not be read: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect the Remote Login user list in System Settings.",),
        )

    membership = run_argv(("/usr/sbin/dseditgroup", "-o", "checkmember", "-m", user_name, group_name))
    if membership.returncode != 0:
        detail = membership.stderr or membership.stdout or membership.failure or "unknown membership failure"
        return SSHDebugCheck(
            identifier="remote_login_access",
            group="permissions",
            label="Remote Login user access",
            status="unknown",
            message=f"Membership in {group_name} could not be verified: {detail}",
            command_suggestions=(),
            manual_advice=("Verify nested and direct membership in the Remote Login access group.",),
        )
    normalized = membership.stdout.casefold()
    if normalized.startswith("yes ") and " is a member of " in normalized:
        return SSHDebugCheck(
            identifier="remote_login_access",
            group="permissions",
            label="Remote Login user access",
            status="ok",
            message=f"Directory Services reports {user_name} is admitted by {group_name}",
            command_suggestions=(),
            manual_advice=(),
        )
    if normalized.startswith("no ") and " is not a member of " in normalized:
        return SSHDebugCheck(
            identifier="remote_login_access",
            group="permissions",
            label="Remote Login user access",
            status="error",
            message=f"Directory Services reports {user_name} is not admitted by {group_name}",
            command_suggestions=(),
            manual_advice=("Add the intended account through the Remote Login user list, not by bypassing the service ACL.",),
        )
    return SSHDebugCheck(
        identifier="remote_login_access",
        group="permissions",
        label="Remote Login user access",
        status="unknown",
        message=f"Directory Services returned unrecognized membership evidence: {membership.stdout or 'empty output'}",
        command_suggestions=(),
        manual_advice=("Inspect the Remote Login user list in System Settings.",),
    )
