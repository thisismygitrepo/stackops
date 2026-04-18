"""Machine status data checks."""

import platform
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict

import stackops.settings.shells.bash as bash_shell_assets
import stackops.settings.shells.pwsh as pwsh_shell_assets
import stackops.utils.path_core as path_core
from stackops.utils.source_of_truth import CONFIG_ROOT, DEFAULTS_PATH
from stackops.utils.links import files_are_identical
from stackops.settings.shells.bash import INIT_PATH_REFERENCE as BASH_INIT_PATH_REFERENCE
from stackops.settings.shells.pwsh import INIT_PATH_REFERENCE as PWSH_INIT_PATH_REFERENCE
from stackops.utils.path_reference import get_path_reference_library_relative_path


def check_shell_profile_status() -> dict[str, Any]:
    """Check shell profile configuration status."""
    from stackops.profile.create_shell_profile import get_shell_profile_path

    try:
        profile_path = get_shell_profile_path()
        if not profile_path.exists():
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.touch()
        profile_content = profile_path.read_text(encoding="utf-8")
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
    from stackops.utils.io import read_ini

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


class ConfigStatusItem(TypedDict):
    config_file_default_path: str
    config_file_self_managed_path: str
    contents: bool | None
    copy: bool | None


def _resolve_config_paths(config_item: ConfigStatusItem) -> tuple[Path, Path]:
    default_path = Path(config_item["config_file_default_path"]).expanduser()
    self_managed_path = Path(
        config_item["config_file_self_managed_path"].replace("CONFIG_ROOT", CONFIG_ROOT.as_posix())
    ).expanduser()
    return default_path, self_managed_path


def _config_item_is_configured(config_item: ConfigStatusItem) -> bool:
    default_path, self_managed_path = _resolve_config_paths(config_item)
    if not default_path.exists() or not self_managed_path.exists():
        return False
    if bool(config_item.get("contents")):
        return default_path.is_dir() and self_managed_path.is_dir()
    try:
        if path_core.resolve(default_path) == path_core.resolve(self_managed_path):
            return True
    except OSError:
        return False
    if default_path.is_symlink():
        return False
    if bool(config_item.get("copy")) and default_path.is_file() and self_managed_path.is_file():
        return files_are_identical(default_path, self_managed_path)
    return False


def _flatten_config_items(mapper_section: Mapping[str, Sequence[ConfigStatusItem]]) -> list[ConfigStatusItem]:
    return [config_item for config_items in mapper_section.values() for config_item in config_items]


def check_config_files_status() -> dict[str, Any]:
    """Check public and private configuration files status."""
    from stackops.profile.create_links import read_mapper

    try:
        mapper = read_mapper(repo="all")
        public_configs = list(mapper.get("public", {}).keys())
        private_configs = list(mapper.get("private", {}).keys())
        public_items = _flatten_config_items(mapper.get("public", {}))
        private_items = _flatten_config_items(mapper.get("private", {}))

        public_count = len(public_items)
        private_count = len(private_items)
        public_linked = sum(1 for config_item in public_items if _config_item_is_configured(config_item))
        private_linked = sum(1 for config_item in private_items if _config_item_is_configured(config_item))

        return {
            "public_count": public_count,
            "public_linked": public_linked,
            "private_count": private_count,
            "private_linked": private_linked,
            "public_program_count": len(public_configs),
            "private_program_count": len(private_configs),
            "public_configs": public_configs,
            "private_configs": private_configs,
        }
    except Exception as ex:
        return {
            "public_count": 0,
            "public_linked": 0,
            "private_count": 0,
            "private_linked": 0,
            "public_program_count": 0,
            "private_program_count": 0,
            "error": str(ex),
            "public_configs": [],
            "private_configs": [],
        }


def check_important_tools() -> dict[str, dict[str, bool]]:
    """Check if important CLI tools are installed, organized by groups."""
    from stackops.jobs.installer.package_groups import PACKAGE_GROUP2NAMES

    group_status: dict[str, dict[str, bool]] = {}
    for group_name, tools in PACKAGE_GROUP2NAMES.items():
        tool_status: dict[str, bool] = {}
        for tool in tools:
            tool_status[tool] = shutil.which(tool) is not None
        group_status[str(group_name)] = tool_status

    return group_status


def check_backup_config() -> dict[str, Any]:
    """Check backup configuration status."""
    from stackops.utils.io import read_ini

    try:
        cloud_config = read_ini(DEFAULTS_PATH)["general"]["rclone_config_name"]
    except (FileNotFoundError, KeyError, IndexError):
        cloud_config = "Not configured"

    try:
        from stackops.scripts.python.helpers.helpers_devops.backup_config import LIBRARY_BACKUP_PATH, read_backup_config

        backup_file = LIBRARY_BACKUP_PATH
        if backup_file.exists():
            backup_data = read_backup_config(repo="library")
            if backup_data is None:
                backup_items = []
                backup_items_count = 0
            else:
                backup_items = []
                for group_name, entries in backup_data.items():
                    backup_items.extend([f"{group_name}.{entry_name}" for entry_name in entries.keys()])
                backup_items_count = len(backup_items)
        else:
            backup_items = []
            backup_items_count = 0
    except Exception:
        backup_items = []
        backup_items_count = 0

    return {"cloud_config": cloud_config, "backup_items_count": backup_items_count, "backup_items": backup_items}
