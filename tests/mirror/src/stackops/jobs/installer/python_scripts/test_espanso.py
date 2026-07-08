from stackops.jobs.installer.python_scripts import espanso
from stackops.utils.schemas.installer.installer_types import InstallerData


def test_alpine_linux_asset_is_explicitly_unavailable() -> None:
    base_installer_data: InstallerData = {
        "appName": "espanso",
        "license": "GPL-3.0",
        "doc": "Text expander",
        "repoURL": espanso.ESPANSO_REPO_URL,
        "categoryLabels": ["productivity-knowledge"],
        "fileNamePattern": {
            "amd64": {"linux": None, "darwin": None, "windows": None},
            "arm64": {"linux": None, "darwin": None, "windows": None},
        },
    }

    installer_data = espanso._build_espanso_installer_data(
        base_installer_data=base_installer_data,
        os_name="linux",
        arch="amd64",
        xdg_session_type="wayland",
    )

    linux_pattern = installer_data["fileNamePattern"]["amd64"]["linux"]
    assert linux_pattern == {
        "apk": None,
        "apt": "espanso-debian-wayland-amd64.deb",
        "dnf": None,
        "pacman": None,
    }
