import json
from typing import cast

import pytest
from jsonschema.validators import Draft7Validator

import stackops.utils.schemas.installer as installer_schema_assets
from stackops.utils.installer_utils import install_request_logic, installer_class, installer_runner
from stackops.utils.installer_utils.github_release_bulk import AssetInfo, ReleaseInfo
from stackops.utils.installer_utils.installer_class import Installer
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, LinuxDistributionId
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import CPU_ARCHITECTURES, OPERATING_SYSTEMS, InstallerData


def test_installer_catalog_matches_schema_and_has_unique_app_names() -> None:
    catalog_path = get_path_reference_path(module=installer_schema_assets, path_reference=installer_schema_assets.INSTALLER_DATA_PATH_REFERENCE)
    schema_path = get_path_reference_path(module=installer_schema_assets, path_reference=installer_schema_assets.INSTALLER_TYPE_SCHEMA_PATH_REFERENCE)
    schema = cast(dict[str, object], json.loads(schema_path.read_text(encoding="utf-8")))
    catalog = cast(dict[str, object], json.loads(catalog_path.read_text(encoding="utf-8")))

    Draft7Validator.check_schema(schema)
    Draft7Validator(schema).validate(catalog)
    installers = cast(list[InstallerData], catalog["installers"])
    app_names = [installer["appName"] for installer in installers]

    assert len(app_names) == len(set(app_names))


@pytest.fixture(scope="module")
def rustdesk_installer_data() -> InstallerData:
    matching_installers = [
        installer for installer in installer_runner.get_installers(os="windows", arch="amd64", which_cats=None) if installer["appName"] == "rustdesk"
    ]
    assert len(matching_installers) == 1
    return matching_installers[0]


@pytest.fixture(scope="module")
def rustdesk_server_installer_data() -> InstallerData:
    matching_installers = [
        installer
        for installer in installer_runner.get_installers(os="windows", arch="amd64", which_cats=None)
        if installer["appName"] == "rustdesk-server"
    ]
    assert len(matching_installers) == 1
    return matching_installers[0]


def test_rustdesk_server_declares_its_complete_binary_set(rustdesk_server_installer_data: InstallerData) -> None:
    assert rustdesk_server_installer_data["executableName"] == "hbbs"
    assert rustdesk_server_installer_data["additionalExecutableNames"] == ["hbbr", "rustdesk-utils"]


@pytest.mark.parametrize(
    ("operating_system", "architecture", "expected_pattern"),
    (
        ("linux", "amd64", "rustdesk_server.py"),
        ("linux", "arm64", "rustdesk_server.py"),
        ("windows", "amd64", "rustdesk_server.py"),
        ("windows", "arm64", None),
        ("darwin", "amd64", None),
        ("darwin", "arm64", None),
    ),
)
def test_rustdesk_server_is_only_available_for_upstream_release_targets(
    operating_system: OPERATING_SYSTEMS, architecture: CPU_ARCHITECTURES, expected_pattern: str | None, rustdesk_server_installer_data: InstallerData
) -> None:
    resolved_pattern = install_request_logic.resolve_installer_pattern(
        installer_data=rustdesk_server_installer_data, operating_system=operating_system, architecture=architecture
    )

    assert resolved_pattern == expected_pattern
    assert Installer(installer_data=rustdesk_server_installer_data).get_exe_name() == "hbbs"


@pytest.mark.parametrize(
    ("architecture", "distribution_id", "expected_pattern"),
    (
        ("amd64", "alpine", None),
        ("amd64", "ubuntu", "rustdesk-{version}-x86_64.deb"),
        ("amd64", "fedora", "rustdesk-{version}-0.x86_64.rpm"),
        ("amd64", "arch", "rustdesk-{version}-0-x86_64.pkg.tar.zst"),
        ("arm64", "alpine", None),
        ("arm64", "ubuntu", "rustdesk-{version}-aarch64.deb"),
        ("arm64", "fedora", "rustdesk-{version}-0.aarch64.rpm"),
        ("arm64", "arch", None),
    ),
)
def test_rustdesk_resolves_exact_linux_package_for_distribution_and_architecture(
    architecture: CPU_ARCHITECTURES,
    distribution_id: LinuxDistributionId,
    expected_pattern: str | None,
    rustdesk_installer_data: InstallerData,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def detect_distribution() -> LinuxDistribution:
        return LinuxDistribution(distribution_id=distribution_id)

    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", detect_distribution)

    resolved_pattern = install_request_logic.resolve_installer_pattern(
        installer_data=rustdesk_installer_data, operating_system="linux", architecture=architecture
    )

    assert resolved_pattern == expected_pattern


@pytest.mark.parametrize(
    ("operating_system", "architecture", "expected_pattern"),
    (
        ("windows", "amd64", "rustdesk-{version}-x86_64.msi"),
        ("windows", "arm64", "rustdesk-{version}-aarch64.msi"),
        ("darwin", "amd64", "rustdesk-{version}-x86_64.dmg"),
        ("darwin", "arm64", "rustdesk-{version}-aarch64.dmg"),
    ),
)
def test_rustdesk_resolves_exact_headed_desktop_installer_pattern(
    operating_system: OPERATING_SYSTEMS, architecture: CPU_ARCHITECTURES, expected_pattern: str, rustdesk_installer_data: InstallerData
) -> None:
    resolved_pattern = install_request_logic.resolve_installer_pattern(
        installer_data=rustdesk_installer_data, operating_system=operating_system, architecture=architecture
    )

    assert resolved_pattern == expected_pattern


@pytest.mark.parametrize(
    ("operating_system", "architecture", "distribution_id", "expected_asset_name"),
    (
        ("linux", "amd64", "ubuntu", "rustdesk-1.4.9-x86_64.deb"),
        ("linux", "amd64", "fedora", "rustdesk-1.4.9-0.x86_64.rpm"),
        ("linux", "amd64", "arch", "rustdesk-1.4.9-0-x86_64.pkg.tar.zst"),
        ("linux", "arm64", "ubuntu", "rustdesk-1.4.9-aarch64.deb"),
        ("linux", "arm64", "fedora", "rustdesk-1.4.9-0.aarch64.rpm"),
        ("windows", "amd64", None, "rustdesk-1.4.9-x86_64.msi"),
        ("windows", "arm64", None, "rustdesk-1.4.9-aarch64.msi"),
        ("darwin", "amd64", None, "rustdesk-1.4.9-x86_64.dmg"),
        ("darwin", "arm64", None, "rustdesk-1.4.9-aarch64.dmg"),
    ),
)
def test_rustdesk_resolves_exact_mocked_github_release_asset_offline(
    operating_system: OPERATING_SYSTEMS,
    architecture: CPU_ARCHITECTURES,
    distribution_id: LinuxDistributionId | None,
    expected_asset_name: str,
    rustdesk_installer_data: InstallerData,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release_version = "1.4.9"
    expected_download_url = f"https://github.com/rustdesk/rustdesk/releases/download/{release_version}/{expected_asset_name}"

    def get_os_name() -> OPERATING_SYSTEMS:
        return operating_system

    def get_architecture() -> CPU_ARCHITECTURES:
        return architecture

    def detect_distribution() -> LinuxDistribution:
        if distribution_id is None:
            raise AssertionError("Linux distribution detection must only run for Linux release resolution.")
        return LinuxDistribution(distribution_id=distribution_id)

    def get_release_info(username: str, repo_name: str, version: str | None) -> ReleaseInfo:
        assert (username, repo_name, version) == ("rustdesk", "rustdesk", release_version)
        asset = AssetInfo(
            name=expected_asset_name,
            size=1,
            download_count=0,
            content_type="application/octet-stream",
            created_at="2026-08-13T00:00:00Z",
            updated_at="2026-08-13T00:00:00Z",
            browser_download_url=expected_download_url,
        )
        return ReleaseInfo(tag_name=release_version, name=release_version, published_at="2026-08-13T00:00:00Z", assets=[asset], assets_count=1)

    monkeypatch.setattr(installer_class, "get_os_name", get_os_name)
    monkeypatch.setattr(installer_class, "get_normalized_arch", get_architecture)
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", detect_distribution)
    monkeypatch.setattr(installer_class, "get_release_info", get_release_info)

    download_url, resolved_version = Installer(installer_data=rustdesk_installer_data).get_github_release(
        repo_url=rustdesk_installer_data["repoURL"], version=release_version
    )

    assert download_url == expected_download_url
    assert resolved_version == release_version
