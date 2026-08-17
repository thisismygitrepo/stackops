import json
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck
from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows_utils import (
    ADMINISTRATORS_SID,
    WindowsIdentity,
    run_powershell,
)


SYSTEM_SID = "S-1-5-18"
READ_DATA_RIGHT = 1
WRITE_RIGHTS_MASK = 2 | 4 | 16 | 256 | 65536 | 262144 | 524288


def _json_object(output: str) -> dict[str, object] | None:
    try:
        parsed: object = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return cast(dict[str, object], parsed)


def _json_object_list(value: object) -> list[dict[str, object]] | None:
    if isinstance(value, dict):
        return [cast(dict[str, object], value)]
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        return None
    return [cast(dict[str, object], item) for item in value]


def check_windows_key_acl(path: Path, identity: WindowsIdentity) -> SSHDebugCheck:
    path_literal = "'" + str(path).replace("'", "''") + "'"
    script = f"""
$acl = Get-Acl -LiteralPath {path_literal}
$rules = @($acl.Access | ForEach-Object {{
    [PSCustomObject]@{{
        Sid = $_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value
        Type = [string]$_.AccessControlType
        Rights = [int64]$_.FileSystemRights
    }}
}})
[PSCustomObject]@{{
    OwnerSid = ($acl.GetOwner([Security.Principal.SecurityIdentifier])).Value
    Rules = @($rules)
}} | ConvertTo-Json -Depth 5 -Compress
"""
    completed = run_powershell(script)
    parsed = _json_object(completed.stdout) if completed.returncode == 0 else None
    if parsed is None:
        detail = completed.stderr or completed.stdout or completed.failure or "invalid ACL output"
        return SSHDebugCheck(
            identifier="authorized_keys_acl",
            group="permissions",
            label="Authorized-keys ACL",
            status="unknown",
            message=f"ACL evidence for {path} could not be read: {detail}",
            command_suggestions=(),
            manual_advice=("Inspect ACL principals as SIDs; do not rely on localized account names.",),
        )
    owner_sid = parsed.get("OwnerSid")
    rules = _json_object_list(parsed.get("Rules"))
    if not isinstance(owner_sid, str) or rules is None:
        return SSHDebugCheck(
            identifier="authorized_keys_acl",
            group="permissions",
            label="Authorized-keys ACL",
            status="unknown",
            message="PowerShell returned malformed ACL evidence",
            command_suggestions=(),
            manual_advice=("Inspect the file owner and DACL by SID.",),
        )

    trusted_sids = {SYSTEM_SID, ADMINISTRATORS_SID} if identity.is_administrator else {SYSTEM_SID, ADMINISTRATORS_SID, identity.sid}
    if owner_sid not in trusted_sids:
        return SSHDebugCheck(
            identifier="authorized_keys_acl",
            group="permissions",
            label="Authorized-keys ACL",
            status="error",
            message=f"{path} owner SID {owner_sid} is not an allowed owner",
            command_suggestions=(),
            manual_advice=("Set ownership using SID-aware Windows ACL tooling.",),
        )

    readable_sids: set[str] = set()
    for rule in rules:
        sid = rule.get("Sid")
        access_type = rule.get("Type")
        rights = rule.get("Rights")
        if not isinstance(sid, str) or not isinstance(access_type, str) or not isinstance(rights, int) or isinstance(rights, bool):
            return SSHDebugCheck(
                identifier="authorized_keys_acl",
                group="permissions",
                label="Authorized-keys ACL",
                status="unknown",
                message="PowerShell returned a malformed access-control entry",
                command_suggestions=(),
                manual_advice=("Inspect every access-control entry by SID.",),
            )
        if access_type == "Deny" and sid in trusted_sids and rights & READ_DATA_RIGHT:
            return SSHDebugCheck(
                identifier="authorized_keys_acl",
                group="permissions",
                label="Authorized-keys ACL",
                status="error",
                message=f"A deny ACE prevents trusted SID {sid} from reading {path}",
                command_suggestions=(),
                manual_advice=("Review explicit and inherited deny entries.",),
            )
        if access_type == "Deny" and rights & READ_DATA_RIGHT:
            return SSHDebugCheck(
                identifier="authorized_keys_acl",
                group="permissions",
                label="Authorized-keys ACL",
                status="unknown",
                message=f"Deny SID {sid} may apply through Windows group membership; effective read access is unproved",
                command_suggestions=(),
                manual_advice=("Use a Windows effective-access check for the user and sshd service identity.",),
            )
        if access_type != "Allow":
            continue
        if rights & READ_DATA_RIGHT:
            readable_sids.add(sid)
        if identity.is_administrator and sid not in trusted_sids and rights:
            return SSHDebugCheck(
                identifier="authorized_keys_acl",
                group="permissions",
                label="Authorized-keys ACL",
                status="error",
                message=f"Untrusted SID {sid} has access to the administrators key file",
                command_suggestions=(),
                manual_advice=("Restrict the file to SYSTEM and built-in Administrators by SID.",),
            )
        if not identity.is_administrator and sid not in trusted_sids and rights & WRITE_RIGHTS_MASK:
            return SSHDebugCheck(
                identifier="authorized_keys_acl",
                group="permissions",
                label="Authorized-keys ACL",
                status="error",
                message=f"Untrusted SID {sid} has write-capable access to {path}",
                command_suggestions=(),
                manual_advice=("Remove write-capable ACEs for untrusted SIDs.",),
            )

    required_readers = {SYSTEM_SID, ADMINISTRATORS_SID} if identity.is_administrator else {identity.sid, SYSTEM_SID}
    if not required_readers.issubset(readable_sids):
        missing = required_readers.difference(readable_sids)
        return SSHDebugCheck(
            identifier="authorized_keys_acl",
            group="permissions",
            label="Authorized-keys ACL",
            status="unknown",
            message=f"Required SID(s) lack a direct readable ACE and may depend on group-granted access: {', '.join(sorted(missing))}",
            command_suggestions=(),
            manual_advice=("Grant only the required principals sufficient read/control rights.",),
        )
    return SSHDebugCheck(
        identifier="authorized_keys_acl",
        group="permissions",
        label="Authorized-keys ACL",
        status="ok",
        message=f"Owner and DACL evidence for {path} is restricted to acceptable SIDs",
        command_suggestions=(),
        manual_advice=(),
    )
