import subprocess
from typing import cast

import pytest

from stackops.utils.installer_utils import install_request_logic, installer_class
from stackops.utils.installer_utils.github_release_bulk import ReleaseInfo
from stackops.utils.schemas.installer.installer_types import InstallRequest, InstallerData


def _build_apt_installer_data(command: str) -> InstallerData:
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
                    "linux": command,
                    "darwin": None,
                    "windows": None,
                },
                "arm64": {
                    "linux": command,
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
                "arm64": {
                    "linux": "pkgx-{version}+linux+aarch64.tar.gz",
                    "darwin": "pkgx-{version}+darwin+aarch64.tar.gz",
                    "windows": None,
                },
            },
        },
    )


def _patch_linux_install_context(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(installer_class, "get_os_name", lambda: "linux")
    monkeypatch.setattr(installer_class, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(installer_class, "check_tool_exists", lambda tool_name: False)
    monkeypatch.setattr(installer_class.Installer, "_read_installed_version", lambda self, exe_name: "")
    monkeypatch.setattr(installer_class, "INSTALL_VERSION_ROOT", tmp_path)
    monkeypatch.setattr(install_request_logic.platform, "system", lambda: "Linux")


def test_sudo_nala_installer_skips_on_non_apt_linux(monkeypatch: pytest.MonkeyPatch, tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    _patch_linux_install_context(monkeypatch=monkeypatch, tmp_path=tmp_path)
    monkeypatch.setattr(
        install_request_logic.platform,
        "freedesktop_os_release",
        lambda: {"ID": "fedora", "ID_LIKE": "rhel fedora"},
    )

    def fail_run(*_args, **_kwargs):
        raise AssertionError("apt-family command should be skipped before subprocess.run")

    monkeypatch.setattr(installer_class.subprocess, "run", fail_run)

    result = installer_class.Installer(_build_apt_installer_data("sudo nala install apt-tool -y")).install_robust(
        install_request=InstallRequest(version=None, update=False)
    )

    assert result["kind"] == "skipped"
    assert "only supported on Debian/Ubuntu-style Linux" in result["detail"]
    output = capsys.readouterr().out
    assert "apt/nala installer skipped" in output
    assert "sudo nala install apt-tool -y" in output


def test_sudo_apt_installer_runs_on_apt_linux(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _patch_linux_install_context(monkeypatch=monkeypatch, tmp_path=tmp_path)
    monkeypatch.setattr(
        install_request_logic.platform,
        "freedesktop_os_release",
        lambda: {"ID": "ubuntu", "ID_LIKE": "debian"},
    )
    commands_run: list[str] = []

    def fake_run(command, *_args, **_kwargs):
        commands_run.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(installer_class.subprocess, "run", fake_run)

    result = installer_class.Installer(_build_apt_installer_data("sudo apt install apt-tool -y")).install_robust(
        install_request=InstallRequest(version=None, update=False)
    )

    assert result["kind"] == "same_version"
    assert commands_run == ["sudo apt install apt-tool -y"]


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
        repo_url="https://github.com/pkgxdev/pkgx",
        version=None,
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

    result = installer_class.Installer(_build_pkgx_installer_data()).get_github_release(
        repo_url="https://github.com/pkgxdev/pkgx",
        version=None,
    )

    assert result == (None, None)
    output = capsys.readouterr().out
    assert "pkgx-other+linux+x86-64.tar.gz" in output
    assert "%2B" not in output
