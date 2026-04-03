from unittest.mock import patch

from machineconfig.scripts.python.helpers.helpers_devops import devops_status


def test_resolve_sections_defaults_to_full_report() -> None:
    sections = devops_status.resolve_sections(machine=False, shell=False, repos=False, ssh=False, configs=False, apps=False, backup=False)

    assert sections == devops_status.ALL_STATUS_SECTIONS


def test_resolve_sections_returns_only_selected_sections() -> None:
    sections = devops_status.resolve_sections(machine=False, shell=True, repos=False, ssh=False, configs=False, apps=True, backup=True)

    assert sections == ("shell", "apps", "backup")


def test_main_runs_only_requested_sections() -> None:
    with (
        patch.object(devops_status, "display_report_header") as display_report_header,
        patch.object(devops_status, "display_report_footer") as display_report_footer,
        patch.object(devops_status, "_run_system_section") as run_system_section,
        patch.object(devops_status, "_run_shell_section") as run_shell_section,
        patch.object(devops_status, "_run_repos_section") as run_repos_section,
        patch.object(devops_status, "_run_ssh_section") as run_ssh_section,
        patch.object(devops_status, "_run_configs_section") as run_configs_section,
        patch.object(devops_status, "_run_apps_section") as run_apps_section,
        patch.object(devops_status, "_run_backup_section") as run_backup_section,
    ):
        devops_status.main(sections=("apps", "backup"))

    display_report_header.assert_called_once_with()
    display_report_footer.assert_called_once_with()
    run_system_section.assert_not_called()
    run_shell_section.assert_not_called()
    run_repos_section.assert_not_called()
    run_ssh_section.assert_not_called()
    run_configs_section.assert_not_called()
    run_apps_section.assert_called_once_with()
    run_backup_section.assert_called_once_with()
