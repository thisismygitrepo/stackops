"""Machine status display."""

from collections.abc import Sequence
from typing import Literal, assert_never, cast

from stackops.scripts.python.helpers.helpers_devops.devops_status_checks import (
    check_backup_config,
    check_config_files_status,
    check_important_tools,
    check_repos_status,
    check_shell_profile_status,
    check_ssh_status,
)
from stackops.scripts.python.helpers.helpers_devops.devops_status_display import (
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


StatusSection = Literal["system", "shell", "repos", "ssh", "configs", "apps", "backup"]

ALL_STATUS_SECTIONS: tuple[StatusSection, ...] = ("system", "shell", "repos", "ssh", "configs", "apps", "backup")


def resolve_sections(
    *,
    machine: bool,
    shell: bool,
    repos: bool,
    ssh: bool,
    configs: bool,
    apps: bool,
    backup: bool,
) -> tuple[StatusSection, ...]:
    """Resolve CLI section flags into the ordered set of sections to display."""
    selected_sections: list[StatusSection] = []
    section_flags: tuple[tuple[bool, StatusSection], ...] = (
        (machine, "system"),
        (shell, "shell"),
        (repos, "repos"),
        (ssh, "ssh"),
        (configs, "configs"),
        (apps, "apps"),
        (backup, "backup"),
    )
    for enabled, section in section_flags:
        if enabled:
            selected_sections.append(section)
    if selected_sections:
        return tuple(selected_sections)
    return ALL_STATUS_SECTIONS


def _run_system_section() -> None:
    from stackops.scripts.python.helpers.helpers_utils.python import get_machine_specs

    system_info = get_machine_specs()
    display_system_info(cast(dict[str, str], system_info))


def _run_shell_section() -> None:
    shell_status = check_shell_profile_status()
    display_shell_status(shell_status)


def _run_repos_section() -> None:
    repos_status = check_repos_status()
    display_repos_status(repos_status)


def _run_ssh_section() -> None:
    ssh_status = check_ssh_status()
    display_ssh_status(ssh_status)


def _run_configs_section() -> None:
    config_status = check_config_files_status()
    display_config_files_status(config_status)


def _run_apps_section() -> None:
    tools_status = check_important_tools()
    display_tools_status(tools_status)


def _run_backup_section() -> None:
    backup_status = check_backup_config()
    display_backup_status(backup_status)


def _run_section(*, section: StatusSection) -> None:
    match section:
        case "system":
            _run_system_section()
        case "shell":
            _run_shell_section()
        case "repos":
            _run_repos_section()
        case "ssh":
            _run_ssh_section()
        case "configs":
            _run_configs_section()
        case "apps":
            _run_apps_section()
        case "backup":
            _run_backup_section()
        case _:
            assert_never(section)


def main(*, sections: Sequence[StatusSection]) -> None:
    """Display the selected machine status sections."""
    display_report_header()
    for section in sections:
        _run_section(section=section)
    display_report_footer()


if __name__ == "__main__":
    main(sections=ALL_STATUS_SECTIONS)
