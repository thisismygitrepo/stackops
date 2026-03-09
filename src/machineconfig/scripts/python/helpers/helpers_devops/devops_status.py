"""Machine Status Display - Comprehensive system and configuration overview"""

from typing import cast

from machineconfig.scripts.python.helpers.helpers_devops.devops_status_checks import (
    _check_backup_config,
    _check_config_files_status,
    _check_important_tools,
    _check_repos_status,
    _check_shell_profile_status,
    _check_ssh_status,
)
from machineconfig.scripts.python.helpers.helpers_devops.devops_status_display import (
    _display_backup_status,
    _display_config_files_status,
    _display_repos_status,
    _display_report_footer,
    _display_report_header,
    _display_shell_status,
    _display_ssh_status,
    _display_system_info,
    _display_tools_status,
)


def main() -> None:
    """Main function to display comprehensive machine status."""
    from machineconfig.scripts.python.helpers.helpers_utils.python import get_machine_specs

    _display_report_header()

    system_info = get_machine_specs()
    _display_system_info(cast(dict[str, str], system_info))

    shell_status = _check_shell_profile_status()
    _display_shell_status(shell_status)

    repos_status = _check_repos_status()
    _display_repos_status(repos_status)

    ssh_status = _check_ssh_status()
    _display_ssh_status(ssh_status)

    config_status = _check_config_files_status()
    _display_config_files_status(config_status)

    tools_status = _check_important_tools()
    _display_tools_status(tools_status)

    backup_status = _check_backup_config()
    _display_backup_status(backup_status)

    _display_report_footer()


if __name__ == "__main__":
    main()
