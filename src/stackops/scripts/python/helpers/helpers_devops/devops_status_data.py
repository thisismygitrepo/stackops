from dataclasses import dataclass
from typing import assert_never, cast

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text

from stackops.scripts.python.helpers.helpers_devops.devops_status_apps import check_important_tools, render_tools_status
from stackops.scripts.python.helpers.helpers_devops.devops_status_backup import check_backup_config, render_backup_status
from stackops.scripts.python.helpers.helpers_devops.devops_status_checks import (
    check_shell_profile_status,
    check_ssh_status,
)
from stackops.scripts.python.helpers.helpers_devops.devops_status_config import check_config_files_status, render_config_files_status
from stackops.scripts.python.helpers.helpers_devops.devops_status_constants import STATUS_TITLES, StatusLevel, StatusSection
from stackops.scripts.python.helpers.helpers_devops.devops_status_display import (
    render_shell_status,
    render_ssh_status,
    render_system_info,
)
from stackops.scripts.python.helpers.helpers_devops.devops_status_repos import check_repos_status, render_repos_status


@dataclass(frozen=True)
class StatusSnapshot:
    summary: str
    level: StatusLevel
    content: RenderableType


def collect_status_section(section: StatusSection) -> StatusSnapshot:
    level: StatusLevel
    try:
        match section:
            case "system":
                from stackops.utils.machine.specs import get_machine_specs

                info = get_machine_specs()
                summary = f"""{info['system']} · {info['machine']}"""
                return StatusSnapshot(summary, "ready", render_system_info(cast(dict[str, str], info)))
            case "shell":
                shell = check_shell_profile_status()
                if shell["configured"]:
                    summary, level = "Configured", "ready"
                else:
                    summary, level = "Not configured", "attention"
                return StatusSnapshot(summary, level, render_shell_status(shell))
            case "repos":
                repos = check_repos_status()
                attention = sum(repository.local.state not in {"Clean", "Bare"} for repository in repos.repositories)
                count = len(repos.repositories)
                noun = "repository" if count == 1 else "repositories"
                summary = f"""{count} {noun} · {attention} need attention""" if count else "No repositories registered"
                return StatusSnapshot(summary, "attention" if attention or not repos.repositories else "ready", render_repos_status(repos))
            case "ssh":
                ssh = check_ssh_status()
                complete = ssh["ssh_dir_exists"] and ssh["config_exists"] and bool(ssh["keys"]) and all(key["private_exists"] for key in ssh["keys"])
                summary = f"""{len(ssh['keys'])} public keys · {'Config found' if ssh['config_exists'] else 'No config'}""" if ssh["ssh_dir_exists"] else "No SSH directory"
                return StatusSnapshot(summary, "ready" if complete else "attention", render_ssh_status(ssh))
            case "configs":
                configs = check_config_files_status()
                linked = configs["public_linked"] + configs["private_linked"]
                total = configs["public_count"] + configs["private_count"]
                level = "ready" if linked == total and total else "attention"
                summary = f"""{linked}/{total} configured"""
                return StatusSnapshot(summary, level, render_config_files_status(configs))
            case "apps":
                tools = check_important_tools()
                unique = {name: installed for group in tools.values() for name, installed in group.items()}
                installed = sum(unique.values())
                summary = f"""{installed} installed · {len(unique)} in catalog"""
                return StatusSnapshot(summary, "ready", render_tools_status(tools))
            case "backup":
                backup = check_backup_config()
                count = backup["backup_items_count"]
                noun = "item" if count == 1 else "items"
                if not count:
                    summary, level = "No registered backup items", "attention"
                elif backup["cloud_selection_required"]:
                    summary, level = f"""{count} backup {noun} · cloud selection required""", "attention"
                else:
                    summary, level = f"""{count} backup {noun}""", "ready"
                return StatusSnapshot(summary, level, render_backup_status(backup))
            case _:
                assert_never(section)
    except Exception as error:
        return StatusSnapshot(
            "Check failed", "error",
            Panel(Text(str(error), style="red"), title=STATUS_TITLES[section], border_style="red"),
        )
