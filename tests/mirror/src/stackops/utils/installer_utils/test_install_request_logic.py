from typing import cast

import pytest

from stackops.utils.installer_utils import install_request_logic
from stackops.utils.installer_utils.linux_package_manager import LinuxDistribution, LinuxDistributionId
from stackops.utils.schemas.installer.installer_types import InstallerData, LinuxInstallerPattern, LinuxPackageManagerInstallerPattern


def _build_installer_data(linux_pattern: LinuxInstallerPattern) -> InstallerData:
    return cast(
        InstallerData,
        {
            "appName": "Native Tool",
            "license": "MIT",
            "doc": "test installer",
            "repoURL": "CMD",
            "categoryLabels": ["system-setup"],
            "fileNamePattern": {
                "amd64": {"windows": None, "linux": linux_pattern, "darwin": None},
                "arm64": {"windows": None, "linux": linux_pattern, "darwin": None},
            },
        },
    )


def _build_native_pattern(*, apt: str | None, dnf: str | None, pacman: str | None) -> LinuxPackageManagerInstallerPattern:
    return {"apt": apt, "dnf": dnf, "pacman": pacman}


def test_portable_linux_pattern_is_returned_without_distribution_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_detection() -> LinuxDistribution:
        raise AssertionError("portable Linux patterns must not depend on the native package manager")

    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", fail_detection)

    resolved_pattern = install_request_logic.resolve_installer_pattern(
        installer_data=_build_installer_data("portable-{version}-linux.tar.gz"), operating_system="linux", architecture="amd64"
    )

    assert resolved_pattern == "portable-{version}-linux.tar.gz"


@pytest.mark.parametrize(
    ("distribution_id", "expected_pattern"),
    [
        ("ubuntu", "sudo apt-get install -y native-tool"),
        ("fedora", "sudo dnf install -y native-tool"),
        ("rhel", "sudo dnf install -y native-tool"),
        ("arch", "sudo pacman -S --needed --noconfirm native-tool"),
    ],
)
def test_native_linux_pattern_uses_detected_package_manager(
    monkeypatch: pytest.MonkeyPatch, distribution_id: LinuxDistributionId, expected_pattern: str
) -> None:
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id=distribution_id))

    resolved_pattern = install_request_logic.resolve_installer_pattern(
        installer_data=_build_installer_data(
            _build_native_pattern(
                apt="sudo apt-get install -y native-tool",
                dnf="sudo dnf install -y native-tool",
                pacman="sudo pacman -S --needed --noconfirm native-tool",
            )
        ),
        operating_system="linux",
        architecture="amd64",
    )

    assert resolved_pattern == expected_pattern


def test_null_pattern_for_detected_package_manager_is_unsupported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="fedora"))

    resolved_pattern = install_request_logic.resolve_installer_pattern(
        installer_data=_build_installer_data(
            _build_native_pattern(apt="sudo apt-get install -y native-tool", dnf=None, pacman="sudo pacman -S --needed --noconfirm native-tool")
        ),
        operating_system="linux",
        architecture="amd64",
    )

    assert resolved_pattern is None


@pytest.mark.parametrize(
    "portable_pattern",
    [
        "sudo apt-get install -y native-tool",
        "sudo dnf install -y native-tool",
        "env DEBIAN_FRONTEND=noninteractive apt-get install -y native-tool",
        "/usr/bin/dnf install -y native-tool",
        "sudo pacman -S --needed --noconfirm native-tool",
        "/usr/bin/pacman -U --noconfirm native-tool.pkg.tar.zst",
        "native-tool-{version}.deb",
        "native-tool-{version}.rpm",
        "native-tool-{version}.pkg.tar.zst",
    ],
)
def test_native_linux_pattern_cannot_masquerade_as_portable(portable_pattern: str) -> None:
    with pytest.raises(ValueError, match="declare it in the required apt/dnf/pacman mapping"):
        install_request_logic.resolve_installer_pattern(
            installer_data=_build_installer_data(portable_pattern), operating_system="linux", architecture="amd64"
        )


def test_incompatible_native_command_cannot_execute_on_selected_package_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="fedora"))

    with pytest.raises(ValueError, match="APT/Nala command"):
        install_request_logic.resolve_installer_pattern(
            installer_data=_build_installer_data(
                _build_native_pattern(
                    apt="sudo apt-get install -y native-tool",
                    dnf="sudo apt-get install -y native-tool",
                    pacman="sudo pacman -S --needed --noconfirm native-tool",
                )
            ),
            operating_system="linux",
            architecture="amd64",
        )


def test_incompatible_unselected_native_command_is_also_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(install_request_logic, "detect_current_linux_distribution", lambda: LinuxDistribution(distribution_id="debian"))

    with pytest.raises(ValueError, match="Linux dnf installer pattern"):
        install_request_logic.resolve_installer_pattern(
            installer_data=_build_installer_data(
                _build_native_pattern(
                    apt="sudo apt-get install -y native-tool",
                    dnf="sudo apt-get install -y native-tool",
                    pacman="sudo pacman -S --needed --noconfirm native-tool",
                )
            ),
            operating_system="linux",
            architecture="amd64",
        )


@pytest.mark.parametrize(
    ("pacman_pattern", "expected_reason"),
    [
        ("sudo apt-get install -y native-tool", "APT/Nala command"),
        ("sudo dnf install -y native-tool", "DNF/YUM command"),
        ("native-tool.deb", "DEB artifact"),
        ("native-tool.rpm", "RPM artifact"),
    ],
)
def test_pacman_mapping_rejects_other_native_ecosystems(pacman_pattern: str, expected_reason: str) -> None:
    with pytest.raises(ValueError, match=expected_reason):
        install_request_logic.resolve_installer_pattern(
            installer_data=_build_installer_data(
                _build_native_pattern(apt="sudo apt-get install -y native-tool", dnf="sudo dnf install -y native-tool", pacman=pacman_pattern)
            ),
            operating_system="linux",
            architecture="amd64",
        )


def test_legacy_yum_command_is_rejected_from_dnf_mapping() -> None:
    with pytest.raises(ValueError, match="legacy YUM command"):
        install_request_logic.resolve_installer_pattern(
            installer_data=_build_installer_data(
                _build_native_pattern(
                    apt="sudo apt-get install -y native-tool",
                    dnf="sudo yum install -y native-tool",
                    pacman="sudo pacman -S --needed --noconfirm native-tool",
                )
            ),
            operating_system="linux",
            architecture="amd64",
        )


@pytest.mark.parametrize(
    "dnf_pattern", ["/usr/bin/yum install -y native-tool", "command nala install -y native-tool", "sudo sh -c 'apt-get install -y native-tool'"]
)
def test_prefixed_incompatible_commands_are_rejected(dnf_pattern: str) -> None:
    with pytest.raises(ValueError):
        install_request_logic.resolve_installer_pattern(
            installer_data=_build_installer_data(
                _build_native_pattern(
                    apt="sudo apt-get install -y native-tool", dnf=dnf_pattern, pacman="sudo pacman -S --needed --noconfirm native-tool"
                )
            ),
            operating_system="linux",
            architecture="amd64",
        )


def test_native_mapping_requires_exact_package_manager_keys() -> None:
    malformed_installer_data = _build_installer_data(cast(LinuxInstallerPattern, {"apt": "sudo apt-get install -y native-tool"}))

    with pytest.raises(ValueError, match="must contain exactly apt, dnf, pacman"):
        install_request_logic.resolve_installer_pattern(installer_data=malformed_installer_data, operating_system="linux", architecture="amd64")


@pytest.mark.parametrize(
    "installer_value", ["apt-get install -y native-tool", "dnf install -y native-tool", "pacman -S --needed --noconfirm native-tool"]
)
def test_native_linux_command_without_sudo_is_a_package_manager_installer(installer_value: str) -> None:
    install_target = install_request_logic.build_install_target(repo_url="CMD", installer_value=installer_value)

    assert install_target.installer_kind == "package_manager"


@pytest.mark.parametrize("installer_value", ["/usr/bin/dnf install -y native-tool", "/usr/bin/pacman -S --needed --noconfirm native-tool"])
def test_path_prefixed_native_command_is_a_package_manager_installer(installer_value: str) -> None:
    install_target = install_request_logic.build_install_target(repo_url="CMD", installer_value=installer_value)

    assert install_target.installer_kind == "package_manager"


def test_pacman_package_download_url_remains_a_binary_url() -> None:
    install_target = install_request_logic.build_install_target(repo_url="CMD", installer_value="https://app.warp.dev/download?package=pacman")

    assert install_target.installer_kind == "binary_url"
