import pytest
import typer

from stackops.jobs.installer import package_groups
from stackops.utils.installer_utils import installer_cli
from stackops.utils.schemas.installer.installer_types import InstallationResultSkipped, InstallRequest, InstallerData


def test_main_installer_cli_installs_all_requested_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_groups: list[str] = []

    def fake_install_group(*, package_group: str, install_request: InstallRequest) -> None:
        _ = install_request
        requested_groups.append(package_group)

    monkeypatch.setattr(installer_cli, "install_group", fake_install_group)

    installer_cli.main_installer_cli(
        which=" editors, agents ",
        group=True,
        interactive=False,
        update=False,
        version=None,
    )

    assert requested_groups == ["editors", "agents"]


def test_install_group_exits_nonzero_for_unknown_group(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(package_groups, "PACKAGE_GROUP2NAMES", {"valid": ["demo"]})

    with pytest.raises(typer.Exit) as exit_info:
        installer_cli.install_group(
            package_group="missing",
            install_request=InstallRequest(version=None, update=False),
        )

    assert exit_info.value.exit_code == 1
    captured = capsys.readouterr()
    assert "Unknown package group: missing" in captured.out


def test_install_clis_resolves_agy_to_antigravity_installer(monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.utils.installer_utils import installer_class, installer_runner, installer_summary
    from stackops.utils.schemas.installer import installer_types

    antigravity_installer: InstallerData = {
        "appName": "antigravity",
        "license": "proprietary",
        "doc": "Antigravity CLI",
        "repoURL": "CMD",
        "fileNamePattern": {
            "amd64": {"linux": "agy install", "darwin": "agy install", "windows": "agy install"},
            "arm64": {"linux": "agy install", "darwin": "agy install", "windows": "agy install"},
        },
    }
    installed_app_names: list[str] = []

    class FakeInstaller:
        def __init__(self, installer_data: InstallerData) -> None:
            self.installer_data = installer_data

        def install_robust(self, install_request: InstallRequest) -> InstallationResultSkipped:
            _ = install_request
            installed_app_names.append(self.installer_data["appName"])
            return {
                "kind": "skipped",
                "appName": self.installer_data["appName"],
                "exeName": "agy",
                "emoji": "⏭️",
                "detail": "already installed, skipped",
            }

    monkeypatch.setattr(installer_types, "get_os_name", lambda: "linux")
    monkeypatch.setattr(installer_types, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(installer_runner, "get_installers", lambda os, arch, which_cats: [antigravity_installer])
    monkeypatch.setattr(installer_class, "Installer", FakeInstaller)
    monkeypatch.setattr(installer_summary, "render_installation_summary", lambda results, console, title: None)

    installer_cli.install_clis(clis_names=["agy"], install_request=InstallRequest(version=None, update=False))

    assert installed_app_names == ["antigravity"]
