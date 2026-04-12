from __future__ import annotations

import pytest

from machineconfig.utils.installer_utils.install_request_logic import InstallTarget
import machineconfig.utils.installer_utils.installer_class as installer_class
from machineconfig.utils.schemas.installer.installer_types import InstallRequest, InstallerData


def _make_installer_data(
    *,
    app_name: str = "My Tool",
    repo_url: str = "https://github.com/owner/repo",
    linux_pattern: str | None = "tool-{version}-linux-amd64.tar.gz",
) -> InstallerData:
    return {
        "appName": app_name,
        "license": "MIT",
        "doc": "example tool",
        "repoURL": repo_url,
        "fileNamePattern": {
            "amd64": {
                "windows": None,
                "linux": linux_pattern,
                "darwin": None,
            },
            "arm64": {
                "windows": None,
                "linux": linux_pattern,
                "darwin": None,
            },
        },
    }


def test_install_robust_returns_skipped_when_tool_already_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installer = installer_class.Installer(_make_installer_data())

    monkeypatch.setattr(installer_class, "get_os_name", lambda: "linux")
    monkeypatch.setattr(installer_class, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(installer_class, "check_tool_exists", lambda tool_name: True)
    monkeypatch.setattr(installer, "_read_installed_version", lambda exe_name: (_ for _ in ()).throw(AssertionError("skip path should not read version")))

    result = installer.install_robust(InstallRequest(version=None, update=False))

    assert result == {
        "kind": "skipped",
        "appName": "My Tool",
        "exeName": "mytool",
        "emoji": "⏭️",
        "detail": "already installed, skipped",
    }


def test_install_robust_returns_updated_when_version_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installer = installer_class.Installer(_make_installer_data())
    observed_requests: list[InstallRequest] = []
    installed_versions = ["1.0.0", "2.0.0"]

    def fake_resolve_install_request(
        install_request: InstallRequest,
    ) -> tuple[InstallTarget, InstallRequest]:
        observed_requests.append(install_request)
        return InstallTarget(installer_kind="github_release", installer_value="tool-{version}.tar.gz"), install_request

    def fake_read_installed_version(exe_name: str) -> str:
        assert exe_name == "mytool"
        return installed_versions.pop(0)

    monkeypatch.setattr(installer_class, "check_tool_exists", lambda tool_name: False)
    monkeypatch.setattr(installer, "_resolve_install_request", fake_resolve_install_request)
    monkeypatch.setattr(installer, "_read_installed_version", fake_read_installed_version)
    monkeypatch.setattr(installer, "_install_requested_with_target", lambda install_target, install_request: None)

    result = installer.install_robust(InstallRequest(version=None, update=False))

    assert observed_requests == [InstallRequest(version=None, update=False)]
    assert result == {
        "kind": "updated",
        "appName": "My Tool",
        "exeName": "mytool",
        "emoji": "🤩",
        "oldVersion": "1.0.0",
        "newVersion": "2.0.0",
    }


def test_install_robust_returns_failed_on_install_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installer = installer_class.Installer(_make_installer_data())

    monkeypatch.setattr(installer_class, "check_tool_exists", lambda tool_name: False)
    monkeypatch.setattr(
        installer,
        "_resolve_install_request",
        lambda install_request: (
            InstallTarget(installer_kind="github_release", installer_value="tool-{version}.tar.gz"),
            install_request,
        ),
    )
    monkeypatch.setattr(installer, "_read_installed_version", lambda exe_name: "1.0.0")

    def fake_install_requested_with_target(
        install_target: InstallTarget,
        install_request: InstallRequest,
    ) -> None:
        _ = install_target, install_request
        raise RuntimeError("boom")

    monkeypatch.setattr(installer, "_install_requested_with_target", fake_install_requested_with_target)

    result = installer.install_robust(InstallRequest(version=None, update=False))

    assert result == {
        "kind": "failed",
        "appName": "My Tool",
        "exeName": "mytool",
        "emoji": "❌",
        "error": "boom",
    }


def test_get_github_release_accepts_filename_variants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installer = installer_class.Installer(_make_installer_data(linux_pattern="tool-{version}-linux-amd64.tar.gz"))

    monkeypatch.setattr(installer_class, "get_os_name", lambda: "linux")
    monkeypatch.setattr(installer_class, "get_normalized_arch", lambda: "amd64")
    monkeypatch.setattr(installer_class, "get_repo_name_from_url", lambda repo_url: ("owner", "repo"))
    monkeypatch.setattr(
        installer_class,
        "get_release_info",
        lambda username, repository, version: {
            "tag_name": "v1.2.3",
            "assets": [
                {
                    "name": "tool_v1.2.3_linux_amd64.tar.gz",
                    "browser_download_url": "https://downloads.example/tool_v1.2.3_linux_amd64.tar.gz",
                }
            ],
        },
    )

    download_url, actual_version = installer.get_github_release("https://github.com/owner/repo", None)

    assert download_url == "https://github.com/owner/repo/releases/download/v1.2.3/tool_v1.2.3_linux_amd64.tar.gz"
    assert actual_version == "v1.2.3"
