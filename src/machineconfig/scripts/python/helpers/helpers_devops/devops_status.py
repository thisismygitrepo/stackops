"""Machine Status Display - Comprehensive system and configuration overview"""

from typing import cast

from machineconfig.scripts.python.helpers.helpers_devops.devops_status_checks import (
    check_backup_config,
    check_config_files_status,
    check_important_tools,
    check_repos_status,
    check_shell_profile_status,
    check_ssh_status,
)
from machineconfig.scripts.python.helpers.helpers_devops.devops_status_display import (
    display_backup_status,
    display_config_files_status,
    display_repos_status,
    display_report_footer,
    display_report_header,
    display_shell_status,
    display_ssh_status,
    display_system_info,
    display_tools_status,
)


def main() -> None:
    """Main function to display comprehensive machine status."""
    from machineconfig.scripts.python.helpers.helpers_utils.python import get_machine_specs

    display_report_header()

    system_info = get_machine_specs()
    display_system_info(cast(dict[str, str], system_info))

    shell_status = check_shell_profile_status()
    display_shell_status(shell_status)

    repos_status = check_repos_status()
    display_repos_status(repos_status)

    ssh_status = check_ssh_status()
    display_ssh_status(ssh_status)

    config_status = check_config_files_status()
    display_config_files_status(config_status)

    tools_status = check_important_tools()
    display_tools_status(tools_status)

    backup_status = check_backup_config()
    display_backup_status(backup_status)

    display_report_footer()


if __name__ == "__main__":
    main()
