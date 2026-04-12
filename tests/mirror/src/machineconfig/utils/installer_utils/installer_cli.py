from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

import pytest

import machineconfig.utils.installer_utils.installer_cli as installer_cli
from machineconfig.utils.schemas.installer.installer_types import InstallRequest, InstallerData


def _make_installer_data(app_name: str) -> InstallerData:
    return {
        "appName": app_name,
        "license": "MIT",
        "doc": f"{app_name} helper",
        "repoURL": "https://github.com/example/repo",
        "fileNamePattern": {
            "amd64": {"windows": None, "linux": "tool-{version}.tar.gz", "darwin": None},
            "arm64": {"windows": None, "linux": "tool-{version}.tar.gz", "darwin": None},
        },
    }


@dataclass(frozen=True, slots=True)
class DuplicateLabelInstaller:
    installer_data: InstallerData

    def get_description(self) -> str:
        _ = self.installer_data
        return "duplicate label"


@dataclass(frozen=True, slots=True)
class RuntimeInstaller:
    installer_data: InstallerData

    def install_robust(self, install_request: InstallRequest) -> dict[str, str]:
        _ = install_request
        return {
            "kind": "updated",
            "appName": self.installer_data["appName"],
            "exeName": self.installer_data["appName"].lower(),
            "emoji": "🤩",
            "oldVersion": "1.0.0",
            "newVersion": "2.0.0",
        }


def test_build_installer_option_to_data_rejects_duplicate_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installers = [_make_installer_data("Alpha"), _make_installer_data("Beta")]
    build_installer_option_to_data = cast(
        Callable[[list[InstallerData]], dict[str, InstallerData]],
        getattr(installer_cli, "_build_installer_option_to_data"),
    )

    monkeypatch.setattr("machineconfig.utils.installer_utils.installer_class.Installer", DuplicateLabelInstaller)

    with pytest.raises(ValueError, match="Duplicate installer option label"):
        build_installer_option_to_data(installers)


def test_build_interactive_option_previews_includes_groups_and_installers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    build_interactive_option_previews = cast(Callable[..., dict[str, str]], getattr(installer_cli, "_build_interactive_option_previews"))

    monkeypatch.setattr(
        "machineconfig.jobs.installer.package_groups.PACKAGE_GROUP2NAMES",
        {"tools": ["alpha", "beta"]},
    )
    installer_option_to_data = {"Alpha": _make_installer_data("Alpha")}

    previews = build_interactive_option_previews(
        category_display_to_name={"Package Tools": "tools"},
        installer_option_to_data=installer_option_to_data,
    )

    group_preview = json.loads(previews["Package Tools"])
    installer_preview = json.loads(previews["Alpha"])

    assert group_preview == {
        "type": "package_group",
        "groupName": "tools",
        "apps": ["alpha", "beta"],
    }
    assert installer_preview["appName"] == "Alpha"


def test_main_installer_cli_routes_interactive_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_requests: list[InstallRequest] = []

    def fake_install_interactively(install_request: InstallRequest) -> None:
        observed_requests.append(install_request)

    monkeypatch.setattr(installer_cli, "install_interactively", fake_install_interactively)

    installer_cli.main_installer_cli(which=None, interactive=True, update=True, version="v3.0.0")

    assert observed_requests == [InstallRequest(version="v3.0.0", update=True)]


def test_install_clis_routes_urls_and_named_installers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_calls: list[tuple[str, str]] = []

    def fake_github_install(github_url: str) -> None:
        observed_calls.append(("github", github_url))

    def fake_binary_install(binary_url: str) -> None:
        observed_calls.append(("binary", binary_url))

    def fake_render_installation_summary(*, results: list[dict[str, str]], console: object, title: str) -> None:
        _ = console
        assert len(results) == 1
        assert title == "📊 Installation Results"
        observed_calls.append(("summary", results[0]["appName"]))

    monkeypatch.setattr("machineconfig.utils.installer_utils.install_from_url.install_from_github_url", fake_github_install)
    monkeypatch.setattr("machineconfig.utils.installer_utils.install_from_url.install_from_binary_url", fake_binary_install)
    monkeypatch.setattr(
        "machineconfig.utils.installer_utils.installer_runner.get_installers",
        lambda os, arch, which_cats: [_make_installer_data("Alpha")],
    )
    monkeypatch.setattr(
        "machineconfig.utils.installer_utils.installer_summary.render_installation_summary",
        fake_render_installation_summary,
    )
    monkeypatch.setattr("machineconfig.utils.installer_utils.installer_class.Installer", RuntimeInstaller)

    installer_cli.install_clis(
        clis_names=["https://github.com/owner/repo", "https://downloads.example/tool", "alpha"],
        install_request=InstallRequest(version=None, update=False),
    )

    assert observed_calls == [
        ("github", "https://github.com/owner/repo"),
        ("binary", "https://downloads.example/tool"),
        ("summary", "Alpha"),
    ]
