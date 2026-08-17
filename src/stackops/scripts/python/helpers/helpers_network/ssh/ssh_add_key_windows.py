import base64
import os
from pathlib import Path
import re
import subprocess

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_keys import PublicKeyRecord, update_authorized_keys


ADMINISTRATORS_SID = "S-1-5-32-544"
SYSTEM_SID = "S-1-5-18"
ELEVATED_INTEGRITY_SIDS: frozenset[str] = frozenset({"S-1-16-12288", "S-1-16-16384"})
SID_PATTERN = re.compile(r"\bS-\d+(?:-\d+)+\b", flags=re.IGNORECASE)


def add_ssh_key_windows(records: list[PublicKeyRecord]) -> tuple[Path, int]:
    group_sids = _read_whoami_sids(arguments=("/groups", "/fo", "csv", "/nh"))
    is_administrator = ADMINISTRATORS_SID in group_sids
    if is_administrator:
        if group_sids.isdisjoint(ELEVATED_INTEGRITY_SIDS):
            raise PermissionError("Administrator accounts must run this command elevated to update ProgramData SSH authorization.")
        program_data = os.environ.get("PROGRAMDATA")
        if program_data is None or program_data == "":
            raise RuntimeError("PROGRAMDATA is unavailable; the administrator SSH authorization path cannot be resolved.")
        ssh_directory = Path(program_data).joinpath("ssh")
        authorized_keys = ssh_directory.joinpath("administrators_authorized_keys")
        ssh_directory.mkdir(parents=True, exist_ok=True)
        authorized_keys.touch(exist_ok=True)
        authorization_trustees = (ADMINISTRATORS_SID, SYSTEM_SID)
        authorization_owner = ADMINISTRATORS_SID
    else:
        user_profile = os.environ.get("USERPROFILE")
        if user_profile is None or user_profile == "":
            raise RuntimeError("USERPROFILE is unavailable; the standard-user SSH authorization path cannot be resolved.")
        user_sids = _read_whoami_sids(arguments=("/user", "/fo", "csv", "/nh"))
        if len(user_sids) != 1:
            raise RuntimeError("Unable to determine the current Windows account SID.")
        user_sid = next(iter(user_sids))
        ssh_directory = Path(user_profile).joinpath(".ssh")
        authorized_keys = ssh_directory.joinpath("authorized_keys")
        ssh_directory.mkdir(parents=True, exist_ok=True)
        authorized_keys.touch(exist_ok=True)
        authorization_trustees = (user_sid, SYSTEM_SID, ADMINISTRATORS_SID)
        authorization_owner = user_sid

    _replace_acl(path=ssh_directory, trustee_sids=authorization_trustees, owner_sid=authorization_owner, directory=True)
    _replace_acl(path=authorized_keys, trustee_sids=authorization_trustees, owner_sid=authorization_owner, directory=False)
    added_count = update_authorized_keys(path=authorized_keys, records=records)
    _replace_acl(path=authorized_keys, trustee_sids=authorization_trustees, owner_sid=authorization_owner, directory=False)
    return authorized_keys, added_count


def _read_whoami_sids(arguments: tuple[str, ...]) -> set[str]:
    completed_process: subprocess.CompletedProcess[str] = subprocess.run(
        [str(_windows_system_executable(name="whoami.exe")), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return {match.upper() for match in SID_PATTERN.findall(completed_process.stdout)}


def _replace_acl(path: Path, trustee_sids: tuple[str, ...], owner_sid: str, directory: bool) -> None:
    encoded_path = base64.b64encode(str(path).encode("utf-8")).decode("ascii")
    trustee_values = ", ".join(f'"{trustee_sid}"' for trustee_sid in trustee_sids)
    directory_literal = "$true" if directory else "$false"
    script = f"""$ErrorActionPreference = "Stop"
$path = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("{encoded_path}"))
$trusteeSids = @({trustee_values})
$ownerSid = "{owner_sid}"
$directory = {directory_literal}
$security = if ($directory) {{
    [System.Security.AccessControl.DirectorySecurity]::new()
}} else {{
    [System.Security.AccessControl.FileSecurity]::new()
}}
$security.SetAccessRuleProtection($true, $false)
$security.SetOwner([System.Security.Principal.SecurityIdentifier]::new($ownerSid))
$inheritance = if ($directory) {{
    [System.Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [System.Security.AccessControl.InheritanceFlags]::ObjectInherit
}} else {{
    [System.Security.AccessControl.InheritanceFlags]::None
}}
foreach ($trusteeSid in $trusteeSids) {{
    $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
        [System.Security.Principal.SecurityIdentifier]::new($trusteeSid),
        [System.Security.AccessControl.FileSystemRights]::FullControl,
        $inheritance,
        [System.Security.AccessControl.PropagationFlags]::None,
        [System.Security.AccessControl.AccessControlType]::Allow
    )
    [void]$security.AddAccessRule($rule)
}}
Set-Acl -LiteralPath $path -AclObject $security
"""
    encoded_script = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    subprocess.run(
        [
            str(_windows_system_executable(name="WindowsPowerShell/v1.0/powershell.exe")),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded_script,
        ],
        check=True,
    )


def _windows_system_executable(name: str) -> Path:
    system_root = os.environ.get("SystemRoot")
    if system_root is None or system_root == "":
        raise RuntimeError(f"SystemRoot is unavailable; {name} cannot be located safely.")
    executable = Path(system_root).joinpath("System32", name)
    if not executable.is_file():
        raise RuntimeError(f"Required Windows executable is unavailable: {executable}")
    return executable
