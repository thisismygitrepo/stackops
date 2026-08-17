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
        authorized_keys = Path("C:/ProgramData/ssh/administrators_authorized_keys")
        authorized_keys.parent.mkdir(parents=True, exist_ok=True)
        authorized_keys.touch(exist_ok=True)
        _apply_file_acl(path=authorized_keys, trustee_sids=(ADMINISTRATORS_SID, SYSTEM_SID))
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
        _apply_directory_acl(path=ssh_directory, trustee_sids=(user_sid, SYSTEM_SID, ADMINISTRATORS_SID))
        _apply_file_acl(path=authorized_keys, trustee_sids=(user_sid, SYSTEM_SID, ADMINISTRATORS_SID))

    added_count = update_authorized_keys(path=authorized_keys, records=records)
    return authorized_keys, added_count


def _read_whoami_sids(arguments: tuple[str, ...]) -> set[str]:
    completed_process: subprocess.CompletedProcess[str] = subprocess.run(
        ["whoami.exe", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return {match.upper() for match in SID_PATTERN.findall(completed_process.stdout)}


def _apply_file_acl(path: Path, trustee_sids: tuple[str, ...]) -> None:
    grants = [f"*{trustee_sid}:F" for trustee_sid in trustee_sids]
    subprocess.run(
        ["icacls.exe", str(path), "/inheritance:r", "/grant:r", *grants],
        check=True,
    )


def _apply_directory_acl(path: Path, trustee_sids: tuple[str, ...]) -> None:
    grants = [f"*{trustee_sid}:(OI)(CI)F" for trustee_sid in trustee_sids]
    subprocess.run(
        ["icacls.exe", str(path), "/inheritance:r", "/grant:r", *grants],
        check=True,
    )
