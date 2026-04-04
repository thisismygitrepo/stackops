from unittest.mock import patch

from rich.console import Console

from machineconfig.utils.installer_utils.install_request_logic import InstallTarget
from machineconfig.utils.installer_utils.installer_class import Installer
from machineconfig.utils.installer_utils.installer_summary import render_installation_summary
from machineconfig.utils.schemas.installer.installer_types import (
    InstallRequest,
    InstallationResultFailed,
    InstallationResultSameVersion,
    InstallationResultSkipped,
    InstallationResultUpdated,
    InstallerData,
)


def _make_installer_data(app_name: str) -> InstallerData:
    return InstallerData(
        appName=app_name,
        license="MIT License",
        doc=f"{app_name} installer",
        repoURL=f"https://github.com/example/{app_name.lower()}",
        fileNamePattern={
            "amd64": {
                "linux": f"{app_name.lower()}-linux.tar.gz",
                "macos": None,
                "windows": None,
            },
            "arm64": {
                "linux": f"{app_name.lower()}-arm64.tar.gz",
                "macos": None,
                "windows": None,
            },
        },
    )


def test_install_robust_returns_structured_updated_result() -> None:
    installer = Installer(installer_data=_make_installer_data(app_name="fd"))
    install_request = InstallRequest(version=None, update=False)

    with (
        patch.object(installer, "_resolve_install_request", return_value=(InstallTarget(installer_kind="github_release", installer_value="fd-linux.tar.gz"), install_request)),
        patch("machineconfig.utils.installer_utils.installer_class.should_skip_install", return_value=False),
        patch.object(installer, "_read_installed_version", side_effect=["fd 1.0.0", "fd 2.0.0"]),
        patch.object(installer, "_install_requested_with_target"),
    ):
        result = installer.install_robust(install_request=install_request)

    assert result == InstallationResultUpdated(
        kind="updated",
        appName="fd",
        exeName="fd",
        emoji="🤩",
        oldVersion="fd 1.0.0",
        newVersion="fd 2.0.0",
    )


def test_install_robust_returns_structured_failed_result() -> None:
    installer = Installer(installer_data=_make_installer_data(app_name="fd"))
    install_request = InstallRequest(version=None, update=False)

    with (
        patch.object(installer, "_resolve_install_request", return_value=(InstallTarget(installer_kind="github_release", installer_value="fd-linux.tar.gz"), install_request)),
        patch("machineconfig.utils.installer_utils.installer_class.should_skip_install", return_value=False),
        patch.object(installer, "_read_installed_version", return_value="fd 1.0.0"),
        patch.object(installer, "_install_requested_with_target", side_effect=RuntimeError("boom")),
    ):
        result = installer.install_robust(install_request=install_request)

    assert result == InstallationResultFailed(
        kind="failed",
        appName="fd",
        exeName="fd",
        emoji="❌",
        error="boom",
    )


def test_render_installation_summary_renders_tables_for_each_result_kind() -> None:
    console = Console(record=True, width=120)
    results = [
        InstallationResultSameVersion(
            kind="same_version",
            appName="tokei",
            exeName="tokei",
            emoji="😑",
            version="tokei 12.0.0",
        ),
        InstallationResultUpdated(
            kind="updated",
            appName="atuin",
            exeName="atuin",
            emoji="🤩",
            oldVersion="atuin 1.0.0",
            newVersion="atuin 2.0.0\nbuild 123",
        ),
        InstallationResultSkipped(
            kind="skipped",
            appName="rg",
            exeName="rg",
            emoji="⏭️",
            detail="already installed, skipped",
        ),
        InstallationResultFailed(
            kind="failed",
            appName="curl",
            exeName="curl",
            emoji="❌",
            error="curl installation failed with return code 2",
        ),
    ]

    render_installation_summary(results=results, console=console, title="📊 Installation Results")

    rendered = console.export_text()
    assert "Same Version Apps" in rendered
    assert "Updated Apps" in rendered
    assert "Skipped Apps" in rendered
    assert "Failed Apps" in rendered
    assert "atuin 2.0.0 build 123" in rendered
