import subprocess
from typing import cast

import pytest

from stackops.utils.installer_utils import install_request_logic, installer_class
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
