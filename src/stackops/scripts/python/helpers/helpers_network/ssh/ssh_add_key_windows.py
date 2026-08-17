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
        _replace_acl(path=ssh_directory, trustee_sids=(ADMINISTRATORS_SID, SYSTEM_SID), owner_sid=ADMINISTRATORS_SID, directory=True)
        _replace_acl(path=authorized_keys, trustee_sids=(ADMINISTRATORS_SID, SYSTEM_SID), owner_sid=ADMINISTRATORS_SID, directory=False)
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
        trustee_sids = (user_sid, SYSTEM_SID, ADMINISTRATORS_SID)
        _replace_acl(path=ssh_directory, trustee_sids=trustee_sids, owner_sid=user_sid, directory=True)
        _replace_acl(path=authorized_keys, trustee_sids=trustee_sids, owner_sid=user_sid, directory=False)

    added_count = update_authorized_keys(path=authorized_keys, records=records)
    if is_administrator:
        _replace_acl(
            path=authorized_keys,
            trustee_sids=(ADMINISTRATORS_SID, SYSTEM_SID),
            owner_sid=ADMINISTRATORS_SID,
            directory=False,
        )
    else:
        _replace_acl(path=authorized_keys, trustee_sids=trustee_sids, owner_sid=user_sid, directory=False)
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
    icacls = str(_windows_system_executable(name="icacls.exe"))
    subprocess.run([icacls, str(path), "/reset"], check=True)
    subprocess.run([icacls, str(path), "/inheritance:r"], check=True)
    permission = "(OI)(CI)F" if directory else "F"
    grants = [f"*{trustee_sid}:{permission}" for trustee_sid in trustee_sids]
    subprocess.run([icacls, str(path), "/grant:r", *grants], check=True)
    subprocess.run([icacls, str(path), "/setowner", f"*{owner_sid}"], check=True)


def _windows_system_executable(name: str) -> Path:
    system_root = os.environ.get("SystemRoot")
    if system_root is None or system_root == "":
        raise RuntimeError(f"SystemRoot is unavailable; {name} cannot be located safely.")
    executable = Path(system_root).joinpath("System32", name)
    if not executable.is_file():
        raise RuntimeError(f"Required Windows executable is unavailable: {executable}")
    return executable
