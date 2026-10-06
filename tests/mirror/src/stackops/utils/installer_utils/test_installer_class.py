from collections.abc import Iterator
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import Mock

import pytest

from stackops.utils.installer_utils import installer_class, package_manager_installation
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.schemas.installer.installer_types import InstallRequest, InstallerData


@pytest.fixture
def version_root(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    temporary_root = Path(".ai/tmp_scripts/winget_result_fix")
    temporary_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=temporary_root) as temporary_directory:
        root = Path(temporary_directory)
        monkeypatch.setattr(installer_class, "INSTALL_VERSION_ROOT", root)
        yield root


@pytest.fixture
def powershell_installer() -> Installer:
    installer_data: InstallerData = {
        "appName": "powershellWinget",
        "license": "MIT License",
        "doc": "PowerShell",
        "repoURL": "CMD",
        "categoryLabels": ["terminals-shells"],
        "fileNamePattern": {
            "amd64": {
                "windows": "winget install --id Microsoft.PowerShell",
                "linux": "winget install --id Microsoft.PowerShell",
                "darwin": "winget install --id Microsoft.PowerShell",
            },
            "arm64": {
                "windows": "winget install --id Microsoft.PowerShell",
                "linux": "winget install --id Microsoft.PowerShell",
                "darwin": "winget install --id Microsoft.PowerShell",
            },
        },
    }
    return Installer(installer_data=installer_data)


@pytest.mark.parametrize("returncode", (2316632107, -1978335189))
def test_winget_update_with_no_changes_reports_same_version_and_preserves_marker(
    returncode: int, powershell_installer: Installer, version_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    installed_version = "PowerShell 7.6.6"
    version_marker = version_root / "pwsh"
    version_marker.write_text("7.6.6", encoding="utf-8")
    run = Mock(return_value=subprocess.CompletedProcess[str](args="winget", returncode=returncode))

    def read_installed_version(self: Installer, exe_name: str) -> str:
        assert self is powershell_installer
        assert exe_name == "pwsh"
        return installed_version

    monkeypatch.setattr(package_manager_installation.subprocess, "run", run)
    monkeypatch.setattr(Installer, "_read_installed_version", read_installed_version)

    result = powershell_installer.install_robust(install_request=InstallRequest(version=None, update=True))

    assert result["kind"] == "same_version"
    assert result["version"] == installed_version
    assert version_marker.read_text(encoding="utf-8") == "7.6.6"


def test_winget_no_update_cannot_satisfy_an_explicit_version_request(
    powershell_installer: Installer, version_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    version_marker = version_root / "pwsh"
    version_marker.write_text("7.6.6", encoding="utf-8")
    run = Mock(return_value=subprocess.CompletedProcess[str](args="winget", returncode=2316632107))

    def read_installed_version(self: Installer, exe_name: str) -> str:
        assert self is powershell_installer
        assert exe_name == "pwsh"
        return "PowerShell 7.6.6"

    monkeypatch.setattr(package_manager_installation.subprocess, "run", run)
    monkeypatch.setattr(Installer, "_read_installed_version", read_installed_version)

    result = powershell_installer.install_robust(install_request=InstallRequest(version="7.7.0", update=True))

    assert result["kind"] == "failed"
    assert "2316632107" in result["error"]
    assert version_marker.read_text(encoding="utf-8") == "7.6.6"
