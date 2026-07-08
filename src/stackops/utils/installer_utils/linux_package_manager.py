from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import platform
from typing import Final, Literal, assert_never


type LinuxDistributionId = Literal[
    "almalinux",
    "centos",
    "debian",
    "deepin",
    "devuan",
    "elementary",
    "fedora",
    "kali",
    "linuxmint",
    "mx",
    "neon",
    "ol",
    "parrot",
    "peppermint",
    "pop",
    "raspbian",
    "rhel",
    "rocky",
    "tuxedo",
    "ubuntu",
    "zorin",
]
type LinuxPackageManager = Literal["apt", "dnf"]
LINUX_PACKAGE_MANAGERS: Final[tuple[LinuxPackageManager, ...]] = ("apt", "dnf")


@dataclass(frozen=True, slots=True)
class LinuxDistribution:
    distribution_id: LinuxDistributionId

    @property
    def package_manager(self) -> LinuxPackageManager:
        return _LINUX_DISTRIBUTION_PACKAGE_MANAGERS[self.distribution_id]


_LINUX_DISTRIBUTION_PACKAGE_MANAGERS: Final[dict[LinuxDistributionId, LinuxPackageManager]] = {
    "debian": "apt",
    "deepin": "apt",
    "devuan": "apt",
    "elementary": "apt",
    "kali": "apt",
    "linuxmint": "apt",
    "mx": "apt",
    "neon": "apt",
    "parrot": "apt",
    "peppermint": "apt",
    "pop": "apt",
    "raspbian": "apt",
    "tuxedo": "apt",
    "ubuntu": "apt",
    "zorin": "apt",
    "almalinux": "dnf",
    "centos": "dnf",
    "fedora": "dnf",
    "ol": "dnf",
    "rhel": "dnf",
    "rocky": "dnf",
}
_LINUX_DISTRIBUTION_ALIASES: Final[dict[str, LinuxDistributionId]] = {"redhat": "rhel"}
_FEDORA_IMMUTABLE_VARIANTS: Final[frozenset[str]] = frozenset({"coreos", "kinoite", "onyx", "sericea", "silverblue"})


class UnsupportedLinuxDistributionError(ValueError):
    distribution_id: str
    id_like: tuple[str, ...]

    def __init__(self, *, distribution_id: str, id_like: tuple[str, ...]) -> None:
        self.distribution_id = distribution_id
        self.id_like = id_like
        supported_ids = sorted({*_LINUX_DISTRIBUTION_PACKAGE_MANAGERS, *_LINUX_DISTRIBUTION_ALIASES})
        detected_id = distribution_id if distribution_id != "" else "<missing>"
        detected_id_like = " ".join(id_like) if len(id_like) > 0 else "<missing>"
        super().__init__(
            f"Unsupported Linux distribution: ID={detected_id!r}, ID_LIKE={detected_id_like!r}. Supported IDs: {', '.join(supported_ids)}"
        )


class UnsupportedOperatingSystemError(RuntimeError):
    operating_system: str

    def __init__(self, *, operating_system: str) -> None:
        self.operating_system = operating_system
        super().__init__(f"Linux package management requires Linux; detected {operating_system!r}")


class UnsupportedLinuxVariantError(ValueError):
    def __init__(self, *, distribution_id: str, variant_id: str) -> None:
        super().__init__(
            f"Linux distribution {distribution_id!r} variant {variant_id!r} uses an immutable "
            "host package workflow; native APT/DNF installation is unsupported."
        )


class UnsupportedLinuxDistributionVersionError(ValueError):
    def __init__(self, *, distribution_id: LinuxDistributionId, version_id: str) -> None:
        displayed_version = version_id if version_id != "" else "<missing>"
        super().__init__(
            f"Linux distribution {distribution_id!r} VERSION_ID={displayed_version!r} is unsupported; "
            "RHEL, CentOS, and Oracle Linux require version 8 or newer for canonical DNF support."
        )


def classify_linux_distribution(os_release: Mapping[str, str]) -> LinuxDistribution:
    distribution_id = _normalize_distribution_id(os_release.get("ID", ""))
    id_like = _normalize_id_like(os_release.get("ID_LIKE", ""))
    variant_id = _normalize_distribution_id(os_release.get("VARIANT_ID", ""))
    is_ostree = os_release.get("OSTREE_VERSION", "").strip() != ""

    if is_ostree or (distribution_id == "fedora" and variant_id in _FEDORA_IMMUTABLE_VARIANTS):
        raise UnsupportedLinuxVariantError(distribution_id=distribution_id, variant_id=variant_id or "ostree")

    registered_distribution_id = _get_registered_distribution_id(distribution_id)
    if registered_distribution_id is not None:
        _validate_distribution_version(distribution_id=registered_distribution_id, version_id=os_release.get("VERSION_ID", ""))
        return LinuxDistribution(distribution_id=registered_distribution_id)

    raise UnsupportedLinuxDistributionError(distribution_id=distribution_id, id_like=id_like)


def detect_current_linux_distribution() -> LinuxDistribution:
    operating_system = platform.system()
    if operating_system != "Linux":
        raise UnsupportedOperatingSystemError(operating_system=operating_system)
    return classify_linux_distribution(platform.freedesktop_os_release())


def build_metadata_refresh_command(package_manager: LinuxPackageManager) -> tuple[str, ...]:
    match package_manager:
        case "apt":
            return ("apt-get", "update")
        case "dnf":
            return ("dnf", "makecache", "--refresh")
    assert_never(package_manager)


def build_package_install_command(package_manager: LinuxPackageManager, packages: Sequence[str]) -> tuple[str, ...]:
    if len(packages) == 0:
        raise ValueError("At least one package is required")
    package_arguments = tuple(packages)
    match package_manager:
        case "apt":
            return ("apt-get", "install", "-y", *package_arguments)
        case "dnf":
            return ("dnf", "install", "-y", *package_arguments)
    assert_never(package_manager)


def _normalize_distribution_id(distribution_id: str) -> str:
    return distribution_id.strip().strip("\"'").lower()


def _get_registered_distribution_id(distribution_id: str) -> LinuxDistributionId | None:
    alias_target = _LINUX_DISTRIBUTION_ALIASES.get(distribution_id)
    if alias_target is not None:
        return alias_target
    if distribution_id in _LINUX_DISTRIBUTION_PACKAGE_MANAGERS:
        return distribution_id
    return None


def _validate_distribution_version(distribution_id: LinuxDistributionId, version_id: str) -> None:
    if distribution_id not in {"rhel", "centos", "ol"}:
        return
    normalized_version_id = version_id.strip().strip("\"'")
    major_version_text = normalized_version_id.split(".", maxsplit=1)[0]
    if not major_version_text.isdecimal() or int(major_version_text) < 8:
        raise UnsupportedLinuxDistributionVersionError(distribution_id=distribution_id, version_id=normalized_version_id)


def _normalize_id_like(raw_id_like: str) -> tuple[str, ...]:
    return tuple(
        normalized_id
        for raw_distribution_id in raw_id_like.replace(",", " ").split()
        if (normalized_id := _normalize_distribution_id(raw_distribution_id)) != ""
    )


def main() -> None:
    distribution = detect_current_linux_distribution()
    print(f"{distribution.distribution_id}\t{distribution.package_manager}")


if __name__ == "__main__":
    main()
