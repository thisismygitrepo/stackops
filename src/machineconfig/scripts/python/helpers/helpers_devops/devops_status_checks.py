"""Machine status data checks."""

import platform
import shutil
from pathlib import Path
from typing import Any

from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.source_of_truth import CONFIG_ROOT, DEFAULTS_PATH


def check_shell_profile_status() -> dict[str, Any]:
    """Check shell profile configuration status."""
    from machineconfig.profile.create_shell_profile import get_shell_profile_path

    try:
        profile_path = get_shell_profile_path()
        if not profile_path.exists():
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.touch()
        profile_content = profile_path.read_text(encoding="utf-8")
        system_name = platform.system()
        if system_name == "Windows":
            init_script = PathExtended(CONFIG_ROOT).joinpath("settings/shells/pwsh/init.ps1")
            init_script_copy = PathExtended(CONFIG_ROOT).joinpath("profile/init.ps1").collapseuser()
            source_reference = f". {str(init_script.collapseuser()).replace('~', '$HOME')}"
            source_copy = f". {str(init_script_copy).replace('~', '$HOME')}"
        else:
            init_script = PathExtended(CONFIG_ROOT).joinpath("settings/shells/bash/init.sh")
            init_script_copy = PathExtended(CONFIG_ROOT).joinpath("profile/init.sh").collapseuser()
            source_reference = f"source {str(init_script.collapseuser()).replace('~', '$HOME')}"
            source_copy = f"source {str(init_script_copy).replace('~', '$HOME')}"

        configured = source_reference in profile_content or source_copy in profile_content
        method = "reference" if source_reference in profile_content else ("copy" if source_copy in profile_content else "none")

        return {
            "profile_path": str(profile_path),
            "exists": True,
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
    """Check configured repositories status."""
    from machineconfig.utils.io import read_ini

    try:
        repos_str = read_ini(DEFAULTS_PATH)["general"]["repos"]
        repo_paths = [Path(p.strip()).expanduser() for p in repos_str.split(",") if p.strip()]

        repos_info = []
        for repo_path in repo_paths:
            if not repo_path.exists():
                repos_info.append({"path": str(repo_path), "name": repo_path.name, "exists": False, "is_repo": False})
                continue

            try:
                import git

                repo = git.Repo(str(repo_path))
                repos_info.append(
                    {
                        "path": str(repo_path),
                        "name": repo_path.name,
                        "exists": True,
                        "is_repo": True,
                        "clean": not repo.is_dirty(untracked_files=True),
                        "branch": repo.active_branch.name if not repo.head.is_detached else "DETACHED",
                    }
                )
            except Exception:
                repos_info.append({"path": str(repo_path), "name": repo_path.name, "exists": True, "is_repo": False})

        return {"configured": True, "count": len(repos_info), "repos": repos_info}
    except (FileNotFoundError, KeyError, IndexError):
        return {"configured": False, "count": 0, "repos": []}


def check_ssh_status() -> dict[str, Any]:
    """Check SSH configuration status."""
    ssh_dir = PathExtended.home().joinpath(".ssh")
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


def check_config_files_status() -> dict[str, Any]:
    """Check public and private configuration files status."""
    from machineconfig.profile.create_links import read_mapper

    try:
        mapper = read_mapper(repo="library")
        public_configs = list(mapper.get("public", {}).keys())
        private_configs = list(mapper.get("private", {}).keys())

        public_count = len(public_configs)
        private_count = len(private_configs)

        public_linked = 0
        for config_name in public_configs:
            for config_item in mapper["public"][config_name]:
                target_path = PathExtended(config_item["config_file_default_path"]).expanduser()
                if target_path.exists():
                    public_linked += 1
                    break

        private_linked = 0
        for config_name in private_configs:
            for config_item in mapper["private"][config_name]:
                target_path = PathExtended(config_item["config_file_default_path"]).expanduser()
                if target_path.exists():
                    private_linked += 1
                    break

        return {
            "public_count": public_count,
            "public_linked": public_linked,
            "private_count": private_count,
            "private_linked": private_linked,
            "public_configs": public_configs,
            "private_configs": private_configs,
        }
    except Exception as ex:
        return {
            "public_count": 0,
            "public_linked": 0,
            "private_count": 0,
            "private_linked": 0,
            "error": str(ex),
            "public_configs": [],
            "private_configs": [],
        }


def check_important_tools() -> dict[str, dict[str, bool]]:
    """Check if important CLI tools are installed, organized by groups."""
    from machineconfig.jobs.installer.package_groups import PACKAGE_GROUP2NAMES

    group_status = {}
    for group_name, tools in PACKAGE_GROUP2NAMES.items():
        tool_status = {}
        for tool in tools:
            tool_status[tool] = shutil.which(tool) is not None
        group_status[group_name] = tool_status

    return group_status


def check_backup_config() -> dict[str, Any]:
    """Check backup configuration status."""
    import tomllib

    from machineconfig.utils.io import read_ini

    try:
        cloud_config = read_ini(DEFAULTS_PATH)["general"]["rclone_config_name"]
    except (FileNotFoundError, KeyError, IndexError):
        cloud_config = "Not configured"

    try:
        from machineconfig.scripts.python.helpers.helpers_devops.backup_config import LIBRARY_BACKUP_PATH

        backup_file = LIBRARY_BACKUP_PATH
        if backup_file.exists():
            backup_data = tomllib.loads(backup_file.read_text(encoding="utf-8"))
            backup_items: list[str] = []
            for group_name, entries in backup_data.items():
                if isinstance(entries, dict):
                    backup_items.extend([f"{group_name}.{entry_name}" for entry_name in entries.keys()])
                else:
                    backup_items.append(str(group_name))
            backup_items_count = len(backup_items)
        else:
            backup_items = []
            backup_items_count = 0
    except Exception:
        backup_items = []
        backup_items_count = 0

    return {"cloud_config": cloud_config, "backup_items_count": backup_items_count, "backup_items": backup_items}
