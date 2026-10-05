"""Machine status data checks."""

import platform
from pathlib import Path
from typing import Any

import stackops.settings.shells.bash as bash_shell_assets
import stackops.settings.shells.pwsh as pwsh_shell_assets
import stackops.utils.path_core as path_core
from stackops.utils.source_of_truth import CONFIG_ROOT
from stackops.settings.shells.bash import INIT_PATH_REFERENCE as BASH_INIT_PATH_REFERENCE
from stackops.settings.shells.pwsh import INIT_PATH_REFERENCE as PWSH_INIT_PATH_REFERENCE
from stackops.utils.path_reference import get_path_reference_library_relative_path


def check_shell_profile_status() -> dict[str, Any]:
    """Check shell profile configuration status."""
    from stackops.profile.create_shell_profile import get_shell_profile_path

    try:
        profile_path = get_shell_profile_path()
        profile_exists = profile_path.exists()
        profile_content = profile_path.read_text(encoding="utf-8") if profile_exists else ""
        system_name = platform.system()
        if system_name == "Windows":
            init_script = Path(CONFIG_ROOT).joinpath(
                get_path_reference_library_relative_path(module=pwsh_shell_assets, path_reference=PWSH_INIT_PATH_REFERENCE)
            )
            init_script_copy = path_core.collapseuser(Path(CONFIG_ROOT).joinpath("profile/init.ps1"), strict=False)
            source_reference = f". {str(path_core.collapseuser(init_script, strict=False)).replace('~', '$HOME')}"
            source_copy = f". {str(init_script_copy).replace('~', '$HOME')}"
        else:
            init_script = Path(CONFIG_ROOT).joinpath(
                get_path_reference_library_relative_path(module=bash_shell_assets, path_reference=BASH_INIT_PATH_REFERENCE)
            )
            init_script_copy = path_core.collapseuser(Path(CONFIG_ROOT).joinpath("profile/init.sh"), strict=False)
            source_reference = f"source {str(path_core.collapseuser(init_script, strict=False)).replace('~', '$HOME')}"
            source_copy = f"source {str(init_script_copy).replace('~', '$HOME')}"

        configured = source_reference in profile_content or source_copy in profile_content
        method = "reference" if source_reference in profile_content else ("copy" if source_copy in profile_content else "none")

        return {
            "profile_path": str(profile_path),
            "exists": profile_exists,
            "configured": configured,
            "method": method,
            "init_script_exists": init_script.exists(),
            "init_script_copy_exists": init_script_copy.exists(),
        }
    except Exception as ex:
        return {
            "profile_path": "Error",
            "exists": False,
            "configured": False,
            "method": "error",
            "error": str(ex),
            "init_script_exists": False,
            "init_script_copy_exists": False,
        }


def check_repos_status() -> dict[str, Any]:
    """Check repository status."""
    return {"configured": False, "count": 0, "repos": []}


def check_ssh_status() -> dict[str, Any]:
    """Check SSH configuration status."""
    ssh_dir = Path.home().joinpath(".ssh")
    if not ssh_dir.exists():
        return {"ssh_dir_exists": False, "keys": [], "config_exists": False, "authorized_keys_exists": False, "known_hosts_exists": False}

    keys = []
    for pub_key in ssh_dir.glob("*.pub"):
        private_key = pub_key.with_suffix("")
        keys.append(
            {
                "name": pub_key.stem,
                "public_exists": True,
                "private_exists": private_key.exists(),
                "public_path": str(pub_key),
                "private_path": str(private_key),
            }
        )

    config_file = ssh_dir.joinpath("config")
    authorized_keys = ssh_dir.joinpath("authorized_keys")
    known_hosts = ssh_dir.joinpath("known_hosts")

    return {
        "ssh_dir_exists": True,
        "keys": keys,
        "config_exists": config_file.exists(),
        "authorized_keys_exists": authorized_keys.exists(),
        "known_hosts_exists": known_hosts.exists(),
        "ssh_dir_path": str(ssh_dir),
    }
