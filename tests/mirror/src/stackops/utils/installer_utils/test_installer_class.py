import subprocess
from pathlib import Path
from typing import cast

import pytest

from stackops.utils.installer_utils import install_request_logic, installer_class
from stackops.utils.installer_utils.github_release_bulk import ReleaseInfo
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution
from stackops.utils.schemas.installer.installer_types import InstallRequest, InstallerData


def _build_native_linux_installer_data(
    apk_command: str | None, apt_command: str | None, dnf_command: str | None, pacman_command: str | None
) -> InstallerData:
    return cast(
        InstallerData,
        {
            "appName": "Apt Tool",
            "license": "unknown",
            "doc": "test installer",
            "repoURL": "CMD",
            "categoryLabels": [],
            "fileNamePattern": {
                "amd64": {
                    "linux": {"apk": apk_command, "apt": apt_command, "dnf": dnf_command, "pacman": pacman_command},
                    "darwin": None,
                    "windows": None,
                },
                "arm64": {
                    "linux": {"apk": apk_command, "apt": apt_command, "dnf": dnf_command, "pacman": pacman_command},
                    "darwin": None,
                    "windows": None,
                },
            },
        },
    )


def _build_pkgx_installer_data() -> InstallerData:
    return cast(
        InstallerData,
        {
            "appName": "pkgx",
            "license": "Apache-2.0",
            "doc": "test GitHub release installer",
            "repoURL": "https://github.com/pkgxdev/pkgx",
            "categoryLabels": [],
            "fileNamePattern": {
                "amd64": {
                    "linux": "pkgx-{version}+linux+x86-64.tar.gz",
                    "darwin": "pkgx-{version}+darwin+x86-64.tar.gz",
                    "windows": "pkgx-{version}+windows+x86-64.zip",
                },
                "arm64": {"linux": "pkgx-{version}+linux+aarch64.tar.gz", "darwin": "pkgx-{version}+darwin+aarch64.tar.gz", "windows": None},
            },
        },
    )


def _patch_linux_install_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(installer_class, "get_os_name", lambda: "linux")
    monkeypatch.setattr(installer_class, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(installer_class, "check_tool_exists", lambda tool_name: False)
    monkeypatch.setattr(installer_class.Installer, "_read_installed_version", lambda self, exe_name: "")
    monkeypatch.setattr(installer_class, "INSTALL_VERSION_ROOT", tmp_path)


def test_native_linux_installer_selects_dnf_on_fedora(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_linux_install_context(monkeypatch=monkeypatch, tmp_path=tmp_path)
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="fedora"))
    commands_run: list[str] = []

    def fake_run(command: str, *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands_run.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(installer_class.subprocess, "run", fake_run)

    result = installer_class.Installer(
        _build_native_linux_installer_data(
            apk_command="sudo apk add native-tool",
            apt_command="sudo apt-get install -y native-tool",
            dnf_command="sudo dnf install -y native-tool",
            pacman_command="sudo pacman -S --needed --noconfirm native-tool",
        )
    ).install_robust(install_request=InstallRequest(version=None, update=False))

    assert result["kind"] == "same_version"
    assert commands_run == ["sudo dnf install -y native-tool"]


def test_native_linux_installer_selects_apt_on_ubuntu(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_linux_install_context(monkeypatch=monkeypatch, tmp_path=tmp_path)
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="ubuntu"))
    commands_run: list[str] = []

    def fake_run(command: str, *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands_run.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(installer_class.subprocess, "run", fake_run)

    result = installer_class.Installer(
        _build_native_linux_installer_data(
            apk_command="sudo apk add native-tool",
            apt_command="sudo apt-get install -y native-tool",
            dnf_command="sudo dnf install -y native-tool",
            pacman_command="sudo pacman -S --needed --noconfirm native-tool",
        )
    ).install_robust(install_request=InstallRequest(version=None, update=False))

    assert result["kind"] == "same_version"
    assert commands_run == ["sudo apt-get install -y native-tool"]


def test_native_linux_installer_selects_pacman_on_arch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_linux_install_context(monkeypatch=monkeypatch, tmp_path=tmp_path)
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="arch"))
    commands_run: list[str] = []

    def fake_run(command: str, *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands_run.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(installer_class.subprocess, "run", fake_run)

    result = installer_class.Installer(
        _build_native_linux_installer_data(
            apk_command="sudo apk add native-tool",
            apt_command="sudo apt-get install -y native-tool",
            dnf_command="sudo dnf install -y native-tool",
            pacman_command="sudo pacman -S --needed --noconfirm native-tool",
        )
    ).install_robust(install_request=InstallRequest(version=None, update=False))

    assert result["kind"] == "same_version"
    assert commands_run == ["sudo pacman -S --needed --noconfirm native-tool"]


def test_native_linux_installer_selects_apk_on_alpine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_linux_install_context(monkeypatch=monkeypatch, tmp_path=tmp_path)
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="alpine"))
    commands_run: list[str] = []

    def fake_run(command: str, *_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands_run.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(installer_class.subprocess, "run", fake_run)

    result = installer_class.Installer(
        _build_native_linux_installer_data(
            apk_command="sudo apk add native-tool",
            apt_command="sudo apt-get install -y native-tool",
            dnf_command="sudo dnf install -y native-tool",
            pacman_command="sudo pacman -S --needed --noconfirm native-tool",
        )
    ).install_robust(install_request=InstallRequest(version=None, update=False))

    assert result["kind"] == "same_version"
    assert commands_run == ["sudo apk add native-tool"]


def test_null_native_linux_pattern_fails_clearly_when_invoked(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_linux_install_context(monkeypatch=monkeypatch, tmp_path=tmp_path)
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="rhel"))

    result = installer_class.Installer(
        _build_native_linux_installer_data(
            apk_command="sudo apk add native-tool",
            apt_command="sudo apt-get install -y native-tool",
            dnf_command=None,
            pacman_command="sudo pacman -S --needed --noconfirm native-tool",
        )
    ).install_robust(install_request=InstallRequest(version=None, update=False))

    assert result["kind"] == "failed"
    assert result["error"] == "No installation pattern for apttool on linux amd64"


def test_direct_arch_package_url_dispatches_to_linux_package_installer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    package_path = tmp_path.joinpath("native-tool.pkg.tar.zst")
    package_path.touch()
    version_root = tmp_path.joinpath("versions")
    installed_packages: list[Path] = []
    monkeypatch.setattr(installer_class, "download_and_prepare", lambda _url: package_path)
    monkeypatch.setattr(installer_class, "install_linux_package_file", installed_packages.append)
    monkeypatch.setattr(installer_class, "INSTALL_VERSION_ROOT", version_root)

    installer_class.Installer(
        _build_native_linux_installer_data(
            apk_command=None, apt_command=None, dnf_command=None, pacman_command="https://example.com/native-tool.pkg.tar.zst"
        )
    )._install_from_value(installer_arch_os="https://example.com/native-tool.pkg.tar.zst", version=None, update=False)

    assert installed_packages == [package_path]
    assert version_root.joinpath("apttool").read_text(encoding="utf-8") == "downloaded_pkg_tar_zst"


def test_direct_apk_package_url_dispatches_to_linux_package_installer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    package_path = tmp_path.joinpath("native-tool.apk")
    package_path.touch()
    version_root = tmp_path.joinpath("versions")
    installed_packages: list[Path] = []
    monkeypatch.setattr(installer_class, "download_and_prepare", lambda _url: package_path)
    monkeypatch.setattr(installer_class, "install_linux_package_file", installed_packages.append)
    monkeypatch.setattr(installer_class, "INSTALL_VERSION_ROOT", version_root)

    installer_class.Installer(
        _build_native_linux_installer_data(
            apk_command="https://example.com/native-tool.apk", apt_command=None, dnf_command=None, pacman_command=None
        )
    )._install_from_value(installer_arch_os="https://example.com/native-tool.apk", version=None, update=False)

    assert installed_packages == [package_path]
    assert version_root.joinpath("apttool").read_text(encoding="utf-8") == "downloaded_apk"


def test_github_release_matches_asset_name_and_returns_api_download_url(monkeypatch: pytest.MonkeyPatch) -> None:
    release_info = ReleaseInfo(
        tag_name="v2.10.3",
        name="v2.10.3",
        published_at="2026-06-26T00:00:00Z",
        assets=[
            {
                "name": "pkgx-2.10.3+linux+x86-64.tar.gz",
                "size": 1,
                "download_count": 1,
                "content_type": "application/gzip",
                "created_at": "2026-06-26T00:00:00Z",
                "updated_at": "2026-06-26T00:00:00Z",
                "browser_download_url": "https://github.com/pkgxdev/pkgx/releases/download/v2.10.3/pkgx-2.10.3%2Blinux%2Bx86-64.tar.gz",
            }
        ],
        assets_count=1,
    )
    monkeypatch.setattr(installer_class, "get_os_name", lambda: "linux")
    monkeypatch.setattr(installer_class, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(installer_class, "get_release_info", lambda _username, _repository, _version: release_info)

    download_url, version = installer_class.Installer(_build_pkgx_installer_data()).get_github_release(
        repo_url="https://github.com/pkgxdev/pkgx", version=None
    )

    assert download_url == "https://github.com/pkgxdev/pkgx/releases/download/v2.10.3/pkgx-2.10.3%2Blinux%2Bx86-64.tar.gz"
    assert version == "v2.10.3"


def test_github_release_debug_table_displays_asset_names(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    release_info = ReleaseInfo(
        tag_name="v2.10.3",
        name="v2.10.3",
        published_at="2026-06-26T00:00:00Z",
        assets=[
            {
                "name": "pkgx-other+linux+x86-64.tar.gz",
                "size": 1,
                "download_count": 1,
                "content_type": "application/gzip",
                "created_at": "2026-06-26T00:00:00Z",
                "updated_at": "2026-06-26T00:00:00Z",
                "browser_download_url": "https://github.com/pkgxdev/pkgx/releases/download/v2.10.3/pkgx-other%2Blinux%2Bx86-64.tar.gz",
            }
        ],
        assets_count=1,
    )
    monkeypatch.setattr(installer_class, "get_os_name", lambda: "linux")
    monkeypatch.setattr(installer_class, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(installer_class, "get_release_info", lambda _username, _repository, _version: release_info)

    result = installer_class.Installer(_build_pkgx_installer_data()).get_github_release(repo_url="https://github.com/pkgxdev/pkgx", version=None)

    assert result == (None, None)
    output = capsys.readouterr().out
    assert "pkgx-other+linux+x86-64.tar.gz" in output
    assert "%2B" not in output
