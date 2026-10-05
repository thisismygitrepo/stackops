import platform
from pathlib import Path
from typing import TypedDict

from stackops.profile.shell_profile_source import build_shell_profile_source
from stackops.utils.source_of_truth import CONFIG_ROOT


class ShellProfileStatus(TypedDict):
    profile_path: str
    exists: bool
    configured: bool
    source_line_present: bool
    init_script_path: str
    init_script_exists: bool


class SshKeyStatus(TypedDict):
    name: str
    public_exists: bool
    private_exists: bool
    public_path: str
    private_path: str


class SshStatus(TypedDict):
    ssh_dir_path: str
    ssh_dir_exists: bool
    config_exists: bool
    authorized_keys_exists: bool
    known_hosts_exists: bool
    keys: list[SshKeyStatus]


def check_shell_profile_status() -> ShellProfileStatus:
    from stackops.profile.create_shell_profile import get_shell_profile_path

    profile_path = get_shell_profile_path()
    profile_source = build_shell_profile_source(system_name=platform.system(), config_root=CONFIG_ROOT)
    profile_exists = profile_path.is_file()
    profile_content = profile_path.read_text(encoding="utf-8") if profile_exists else ""
    source_line_present = any(line.strip() == profile_source.source_line for line in profile_content.splitlines())
    init_script_exists = profile_source.init_script.is_file()
    return {
        "profile_path": str(profile_path),
        "exists": profile_exists,
        "configured": source_line_present and init_script_exists,
        "source_line_present": source_line_present,
        "init_script_path": str(profile_source.init_script),
        "init_script_exists": init_script_exists,
    }


def check_ssh_status() -> SshStatus:
    ssh_dir = Path.home().joinpath(".ssh")
    ssh_dir_exists = ssh_dir.is_dir()
    keys: list[SshKeyStatus] = []
    if ssh_dir_exists:
        for public_key in sorted(ssh_dir.iterdir()):
            if public_key.suffix != ".pub" or public_key.name.endswith("-cert.pub") or not public_key.is_file():
                continue
            private_key = public_key.with_suffix("")
            keys.append(
                {
                    "name": public_key.stem,
                    "public_exists": True,
                    "private_exists": private_key.is_file(),
                    "public_path": str(public_key),
                    "private_path": str(private_key),
                }
            )
    return {
        "ssh_dir_path": str(ssh_dir),
        "ssh_dir_exists": ssh_dir_exists,
        "keys": keys,
        "config_exists": ssh_dir.joinpath("config").is_file(),
        "authorized_keys_exists": ssh_dir.joinpath("authorized_keys").is_file(),
        "known_hosts_exists": ssh_dir.joinpath("known_hosts").is_file(),
    }
