from pathlib import Path
from unittest.mock import patch

from machineconfig.scripts.python.helpers.helpers_devops import devops_status
from machineconfig.scripts.python.helpers.helpers_devops import devops_status_checks


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


def test_check_config_files_status_counts_mapped_items_from_all_repos(tmp_path: Path) -> None:
    public_managed_path = tmp_path / "public-managed.toml"
    public_default_path = tmp_path / "public-default.toml"
    public_missing_default_path = tmp_path / "public-missing.toml"
    public_missing_managed_path = tmp_path / "public-missing-managed.toml"
    private_managed_path = tmp_path / "private-managed.toml"
    private_default_path = tmp_path / "private-default.toml"

    public_managed_path.write_text("public", encoding="utf-8")
    public_default_path.symlink_to(public_managed_path)
    public_missing_managed_path.write_text("missing", encoding="utf-8")
    private_managed_path.write_text("private", encoding="utf-8")
    private_default_path.write_text("private", encoding="utf-8")

    mapper: dict[str, dict[str, list[devops_status_checks.ConfigStatusItem]]] = {
        "public": {
            "demo": [
                {
                    "config_file_default_path": str(public_default_path),
                    "config_file_self_managed_path": str(public_managed_path),
                    "contents": None,
                    "copy": None,
                },
                {
                    "config_file_default_path": str(public_missing_default_path),
                    "config_file_self_managed_path": str(public_missing_managed_path),
                    "contents": None,
                    "copy": None,
                },
            ]
        },
        "private": {
            "secret": [
                {
                    "config_file_default_path": str(private_default_path),
                    "config_file_self_managed_path": str(private_managed_path),
                    "contents": None,
                    "copy": True,
                }
            ]
        },
    }

    with patch("machineconfig.profile.create_links.read_mapper", return_value=mapper) as read_mapper:
        status = devops_status_checks.check_config_files_status()

    read_mapper.assert_called_once_with(repo="all")
    assert status["public_count"] == 2
    assert status["public_linked"] == 1
    assert status["private_count"] == 1
    assert status["private_linked"] == 1
    assert status["public_program_count"] == 1
    assert status["private_program_count"] == 1
