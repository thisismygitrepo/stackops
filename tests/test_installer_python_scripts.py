from unittest.mock import patch

import pytest

from machineconfig.jobs.installer.python_scripts import dubdb_adbc, espanso
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def _make_script_installer_data(app_name: str, script_name: str) -> InstallerData:
    return InstallerData(
        appName=app_name,
        license="MIT License",
        doc=f"{app_name} installer",
        repoURL="CMD",
        fileNamePattern={
            "amd64": {
                "linux": script_name,
                "darwin": script_name,
                "windows": script_name,
            },
            "arm64": {
                "linux": script_name,
                "darwin": script_name,
                "windows": script_name,
            },
        },
    )


def test_build_espanso_installer_data_uses_windows_portable_zip() -> None:
    installer_data = _make_script_installer_data(app_name="espanso", script_name="espanso.py")

    resolved = espanso._build_espanso_installer_data(  # pyright: ignore[reportPrivateUsage]
        base_installer_data=installer_data,
        os_name="windows",
        arch="amd64",
        xdg_session_type=None,
    )

    assert resolved["repoURL"] == espanso.ESPANSO_REPO_URL
    assert resolved["fileNamePattern"]["amd64"]["windows"] == espanso.ESPANSO_WINDOWS_PORTABLE_ASSET


def test_build_espanso_installer_data_uses_linux_wayland_deb() -> None:
    installer_data = _make_script_installer_data(app_name="espanso", script_name="espanso.py")

    resolved = espanso._build_espanso_installer_data(  # pyright: ignore[reportPrivateUsage]
        base_installer_data=installer_data,
        os_name="linux",
        arch="amd64",
        xdg_session_type="wayland",
    )

    assert resolved["repoURL"] == espanso.ESPANSO_REPO_URL
    assert resolved["fileNamePattern"]["amd64"]["linux"] == "espanso-debian-wayland-amd64.deb"


def test_build_espanso_installer_data_rejects_windows_arm64() -> None:
    installer_data = _make_script_installer_data(app_name="espanso", script_name="espanso.py")

    with pytest.raises(NotImplementedError, match="Windows portable builds for amd64"):
        espanso._build_espanso_installer_data(  # pyright: ignore[reportPrivateUsage]
            base_installer_data=installer_data,
            os_name="windows",
            arch="arm64",
            xdg_session_type=None,
        )


def test_dubdb_main_uses_module_installer_data() -> None:
    recursive_installer_data = _make_script_installer_data(app_name="duckdb", script_name="dubdb_adbc.py")
    created_installer_data: list[InstallerData] = []
    installed_versions: list[str | None] = []

    class FakeInstaller:
        def __init__(self, installer_data: InstallerData) -> None:
            created_installer_data.append(installer_data)

        def install(self, version: str | None) -> None:
            installed_versions.append(version)

    with patch("machineconfig.jobs.installer.python_scripts.dubdb_adbc.Installer", FakeInstaller):
        dubdb_adbc.main(installer_data=recursive_installer_data, version="v1.2.3", update=False)

    assert created_installer_data == [dubdb_adbc.DUCKDB_INSTALLER_DATA]
    assert installed_versions == ["v1.2.3"]
