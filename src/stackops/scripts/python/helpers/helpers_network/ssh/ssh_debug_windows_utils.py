import json
import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_common import CommandResult, SSHDSettings, run_argv
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


ADMINISTRATORS_SID = "S-1-5-32-544"


@dataclass(frozen=True, slots=True)
class WindowsIdentity:
    name: str
    sid: str
    is_administrator: bool


@dataclass(frozen=True, slots=True)
class WindowsIdentityAssessment:
    identity: WindowsIdentity | None
    check: SSHDebugCheck


def run_powershell(script: str) -> CommandResult:
    argv = ("powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script)
    completed = run_argv(argv)
    return completed


def _json_object(output: str) -> dict[str, object] | None:
    try:
        parsed: object = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return cast(dict[str, object], parsed)


def find_windows_sshd() -> Path | None:
    windows_directory = Path(os.environ.get("WINDIR", "C:/Windows"))
    candidates = (
        windows_directory.joinpath("System32/OpenSSH/sshd.exe"),
        Path("C:/Program Files/OpenSSH/sshd.exe"),
        Path("C:/Program Files (x86)/OpenSSH/sshd.exe"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    discovered = shutil.which("sshd.exe")
    if discovered is not None:
        return Path(discovered)
    return None


def windows_sshd_config_path() -> Path:
    program_data = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
    config_directory = program_data.joinpath("ssh")
    return config_directory.joinpath("sshd_config")


def assess_windows_identity() -> WindowsIdentityAssessment:
    script = """
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$groupSids = @($identity.Groups | ForEach-Object { $_.Value })
[PSCustomObject]@{
    Name = $identity.Name
    Sid = $identity.User.Value
    IsAdministrator = $groupSids -contains 'S-1-5-32-544'
} | ConvertTo-Json -Compress
"""
    completed = run_powershell(script)
    parsed = _json_object(completed.stdout) if completed.returncode == 0 else None
    if parsed is None:
        detail = completed.stderr or completed.stdout or completed.failure or "invalid identity output"
        return WindowsIdentityAssessment(
            identity=None,
            check=SSHDebugCheck(
                identifier="administrator_membership",
                group="permissions",
                label="Administrator membership",
                status="unknown",
                message=f"Current token groups could not be read by SID: {detail}",
                command_suggestions=(),
                manual_advice=("Determine group membership by SID S-1-5-32-544, not by elevation state or a localized name.",),
            ),
        )
    name = parsed.get("Name")
    sid = parsed.get("Sid")
    is_administrator = parsed.get("IsAdministrator")
    if not isinstance(name, str) or not isinstance(sid, str) or not isinstance(is_administrator, bool):
        return WindowsIdentityAssessment(
            identity=None,
            check=SSHDebugCheck(
                identifier="administrator_membership",
                group="permissions",
                label="Administrator membership",
                status="unknown",
                message="PowerShell returned malformed identity data",
                command_suggestions=(),
                manual_advice=("Inspect the current Windows identity and group SIDs.",),
            ),
        )
    identity = WindowsIdentity(name=name, sid=sid, is_administrator=is_administrator)
    account_kind = "member of built-in Administrators" if is_administrator else "not a member of built-in Administrators"
    return WindowsIdentityAssessment(
        identity=identity,
        check=SSHDebugCheck(
            identifier="administrator_membership",
            group="permissions",
            label="Administrator membership",
            status="ok",
            message=f"{name} is {account_kind}; membership was determined from SID {ADMINISTRATORS_SID}",
            command_suggestions=(),
            manual_advice=(),
        ),
    )


def check_windows_service() -> SSHDebugCheck:
    script = """
$service = Get-Service -Name sshd -ErrorAction SilentlyContinue
if ($null -eq $service) {
    [PSCustomObject]@{ Found = $false; Status = $null } | ConvertTo-Json -Compress
} else {
    [PSCustomObject]@{ Found = $true; Status = [string]$service.Status } | ConvertTo-Json -Compress
}
"""
    completed = run_powershell(script)
    parsed = _json_object(completed.stdout) if completed.returncode == 0 else None
    if parsed is None:
        detail = completed.stderr or completed.stdout or completed.failure or "invalid service output"
        return SSHDebugCheck(
            identifier="ssh_service",
            group="service",
            label="SSH service",
            status="unknown",
            message=f"The sshd service could not be queried: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect the sshd service without assuming that query failure means it is healthy.",),
        )
    found = parsed.get("Found")
    status = parsed.get("Status")
    if found is False:
        return SSHDebugCheck(
            identifier="ssh_service",
            group="service",
            label="SSH service",
            status="error",
            message="The sshd Windows service is not registered",
            command_suggestions=(),
            manual_advice=("Install or register OpenSSH Server using the supported Windows administration workflow.",),
        )
    if found is True and status == "Running":
        return SSHDebugCheck(
            identifier="ssh_service",
            group="service",
            label="SSH service",
            status="ok",
            message="The sshd Windows service is Running",
            command_suggestions=(),
            manual_advice=(),
        )
    if found is True and isinstance(status, str):
        return SSHDebugCheck(
            identifier="ssh_service",
            group="service",
            label="SSH service",
            status="error",
            message=f"The sshd Windows service is {status}",
            command_suggestions=("Start-Service -Name sshd",),
            manual_advice=("Review the sshd service event log before changing startup behavior.",),
        )
    return SSHDebugCheck(
        identifier="ssh_service",
        group="service",
        label="SSH service",
        status="unknown",
        message="PowerShell returned malformed sshd service data",
        command_suggestions=(),
        manual_advice=("Inspect the sshd service manually.",),
    )


def resolve_windows_authorized_key_path(
    settings: SSHDSettings | None,
    identity: WindowsIdentity,
    home_directory: Path,
) -> Path | None:
    program_data = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
    if settings is None:
        return program_data.joinpath("ssh/administrators_authorized_keys") if identity.is_administrator else None
    configured_values = settings.values.get("authorizedkeysfile", ())
    resolved_paths: list[Path] = []
    for configured_value in configured_values:
        try:
            configured_paths = shlex.split(configured_value, comments=False, posix=True)
        except ValueError:
            return None
        for configured_path in configured_paths:
            if configured_path == "none":
                continue
            expanded = configured_path.replace("__PROGRAMDATA__", str(program_data))
            expanded = expanded.replace("%h", str(home_directory)).replace("%u", identity.name)
            if "%" in expanded:
                return None
            path = Path(expanded)
            resolved_paths.append(path if path.is_absolute() else home_directory.joinpath(path))
    if identity.is_administrator:
        non_home_paths = [path for path in resolved_paths if not path.is_relative_to(home_directory)]
        if non_home_paths:
            return non_home_paths[0]
        return program_data.joinpath("ssh/administrators_authorized_keys")
    if resolved_paths:
        return resolved_paths[0]
    return None
