from typing import get_args

import pytest

from stackops.utils.installer_utils import linux_package_manager
from stackops.utils.installer_utils.linux_package_manager import LINUX_PACKAGE_MANAGERS, LinuxDistribution, LinuxDistributionId, LinuxPackageManager


def test_distribution_registry_covers_every_typed_distribution_id() -> None:
    declared_distribution_ids = set(get_args(LinuxDistributionId.__value__))
    registered_distribution_ids = set(linux_package_manager._LINUX_DISTRIBUTION_PACKAGE_MANAGERS)

    assert registered_distribution_ids == declared_distribution_ids


def test_package_manager_iteration_covers_every_typed_manager() -> None:
    declared_package_managers = set(get_args(LinuxPackageManager.__value__))

    assert set(LINUX_PACKAGE_MANAGERS) == declared_package_managers


@pytest.mark.parametrize("distribution_id", ["ubuntu", "debian"])
def test_classifies_debian_ecosystem_distributions(distribution_id: LinuxDistributionId) -> None:
    result = linux_package_manager.classify_linux_distribution({"ID": distribution_id, "ID_LIKE": "debian"})

    assert result == LinuxDistribution(distribution_id=distribution_id)


@pytest.mark.parametrize("distribution_id", ["rhel", "fedora"])
def test_classifies_red_hat_ecosystem_distributions(distribution_id: LinuxDistributionId) -> None:
    result = linux_package_manager.classify_linux_distribution({"ID": distribution_id, "ID_LIKE": "rhel fedora", "VERSION_ID": "9.4"})

    assert result == LinuxDistribution(distribution_id=distribution_id)


@pytest.mark.parametrize("distribution_id", ["rocky", "almalinux"])
def test_classifies_registered_red_hat_derivatives(distribution_id: LinuxDistributionId) -> None:
    result = linux_package_manager.classify_linux_distribution({"ID": distribution_id, "ID_LIKE": "rhel fedora"})

    assert result == LinuxDistribution(distribution_id=distribution_id)


def test_classifies_oracle_linux_8_10_as_dnf() -> None:
    result = linux_package_manager.classify_linux_distribution({"ID": "ol", "ID_LIKE": "fedora", "VERSION_ID": "8.10"})

    assert result == LinuxDistribution(distribution_id="ol")
    assert result.package_manager == "dnf"


def test_missing_id_is_not_inferred_from_id_like() -> None:
    with pytest.raises(linux_package_manager.UnsupportedLinuxDistributionError, match="ID='<missing>'.*ID_LIKE='rhel fedora'"):
        linux_package_manager.classify_linux_distribution({"ID_LIKE": "rhel fedora", "VERSION_ID": "9"})


def test_unregistered_derivative_must_be_added_explicitly() -> None:
    with pytest.raises(linux_package_manager.UnsupportedLinuxDistributionError, match="acme-rocky-workstation"):
        linux_package_manager.classify_linux_distribution({"ID": "acme-rocky-workstation", "ID_LIKE": "rocky rhel fedora"})


def test_distribution_id_takes_priority_over_conflicting_id_like() -> None:
    result = linux_package_manager.classify_linux_distribution({"ID": "ubuntu", "ID_LIKE": "rhel fedora"})

    assert result == LinuxDistribution(distribution_id="ubuntu")


def test_normalizes_red_hat_distribution_alias() -> None:
    result = linux_package_manager.classify_linux_distribution({"ID": "redhat", "VERSION_ID": "9"})

    assert result.distribution_id == "rhel"
    assert result.package_manager == "dnf"


@pytest.mark.parametrize("distribution_id", ["amzn", "oracle"])
def test_version_ambiguous_distributions_are_not_inferred(distribution_id: str) -> None:
    with pytest.raises(linux_package_manager.UnsupportedLinuxDistributionError):
        linux_package_manager.classify_linux_distribution({"ID": distribution_id, "ID_LIKE": "rhel fedora"})


@pytest.mark.parametrize(
    "os_release",
    [
        {"ID": "fedora", "VARIANT_ID": "silverblue"},
        {"ID": "fedora", "VARIANT_ID": "coreos"},
        {"ID": "fedora", "VARIANT_ID": "workstation", "OSTREE_VERSION": "44.20260701.0"},
    ],
)
def test_immutable_linux_variants_are_rejected(os_release: dict[str, str]) -> None:
    with pytest.raises(linux_package_manager.UnsupportedLinuxVariantError, match="immutable host package workflow"):
        linux_package_manager.classify_linux_distribution(os_release)


@pytest.mark.parametrize("distribution_id", ["rhel", "centos", "ol"])
@pytest.mark.parametrize("version_id", ["", "7", "7.9", "rolling"])
def test_pre_dnf_enterprise_releases_are_rejected(distribution_id: LinuxDistributionId, version_id: str) -> None:
    with pytest.raises(linux_package_manager.UnsupportedLinuxDistributionVersionError, match="version 8 or newer"):
        linux_package_manager.classify_linux_distribution({"ID": distribution_id, "VERSION_ID": version_id})


def test_unknown_distribution_error_includes_os_release_details() -> None:
    with pytest.raises(linux_package_manager.UnsupportedLinuxDistributionError, match="ID='plan9'.*ID_LIKE='unix custom'") as error:
        linux_package_manager.classify_linux_distribution({"ID": "plan9", "ID_LIKE": "unix custom"})

    assert error.value.distribution_id == "plan9"
    assert error.value.id_like == ("unix", "custom")


def test_current_distribution_rejects_non_linux_before_reading_os_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(linux_package_manager.platform, "system", lambda: "Darwin")

    def fail_read_os_release() -> dict[str, str]:
        raise AssertionError("freedesktop_os_release must only be read on Linux")

    monkeypatch.setattr(linux_package_manager.platform, "freedesktop_os_release", fail_read_os_release)

    with pytest.raises(linux_package_manager.UnsupportedOperatingSystemError, match="requires Linux; detected 'Darwin'"):
        linux_package_manager.detect_current_linux_distribution()


def test_current_distribution_reads_freedesktop_os_release(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(linux_package_manager.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        linux_package_manager.platform, "freedesktop_os_release", lambda: {"ID": "centos", "ID_LIKE": "rhel fedora", "VERSION_ID": "9"}
    )

    assert linux_package_manager.detect_current_linux_distribution() == LinuxDistribution(distribution_id="centos")


@pytest.mark.parametrize(("package_manager", "expected_command"), [("apt", ("apt-get", "update")), ("dnf", ("dnf", "makecache", "--refresh"))])
def test_builds_metadata_refresh_commands(package_manager: LinuxPackageManager, expected_command: tuple[str, ...]) -> None:
    assert linux_package_manager.build_metadata_refresh_command(package_manager) == expected_command


@pytest.mark.parametrize(
    ("package_manager", "expected_command"), [("apt", ("apt-get", "install", "-y", "curl", "git")), ("dnf", ("dnf", "install", "-y", "curl", "git"))]
)
def test_builds_package_install_commands(package_manager: LinuxPackageManager, expected_command: tuple[str, ...]) -> None:
    assert linux_package_manager.build_package_install_command(package_manager, ["curl", "git"]) == expected_command


def test_package_install_command_requires_packages() -> None:
    with pytest.raises(ValueError, match="At least one package is required"):
        linux_package_manager.build_package_install_command("dnf", [])
