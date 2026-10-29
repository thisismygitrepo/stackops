import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, NotRequired, TypeAlias, TypedDict, get_args


CPU_ARCHITECTURES: TypeAlias = Literal["amd64", "arm64"]
OPERATING_SYSTEMS: TypeAlias = Literal["windows", "linux", "darwin"]
InstallerDataSource: TypeAlias = Literal["library", "l", "user", "u", "all", "a"]
NormalizedInstallerDataSource: TypeAlias = Literal["library", "user", "all"]
INSTALLER_DATA_SOURCE_MAP: Final[dict[InstallerDataSource, NormalizedInstallerDataSource]] = {
    "library": "library",
    "l": "library",
    "user": "user",
    "u": "user",
    "all": "all",
    "a": "all",
}
InstallerCategoryLabel: TypeAlias = Literal[
    "system-setup",
    "languages-runtimes",
    "editors-ides",
    "version-control",
    "build-devops-containers",
    "ai-agents-assistants",
    "terminals-shells",
    "terminal-workspaces",
    "search-navigation",
    "file-managers",
    "file-operations-archives",
    "storage-backup-sync",
    "data-format-tools",
    "databases",
    "networking-diagnostics",
    "tunnels-remote-access",
    "file-transfer-sharing",
    "cloud-saas",
    "browsers-web-access",
    "web-scraping-conversion",
    "documents-markdown-latex",
    "graphics-images-ocr-diagrams",
    "media-audio-video",
    "presentations-recording",
    "productivity-knowledge",
    "security-credentials-privacy",
    "monitoring-performance",
    "qr-mobile-device-tools",
    "terminal-fun-visuals",
    "email-communications",
    "finance-markets",
    "windows-platform",
]
INSTALLER_CATEGORY_LABELS: Final[tuple[InstallerCategoryLabel, ...]] = get_args(InstallerCategoryLabel)


class LinuxPackageManagerInstallerPattern(TypedDict):
    apk: str | None
    apt: str | None
    dnf: str | None
    pacman: str | None
    omarchy: NotRequired[str | None]


LinuxInstallerPattern: TypeAlias = str | None | LinuxPackageManagerInstallerPattern


class ArchitectureInstallerPattern(TypedDict):
    linux: LinuxInstallerPattern
    darwin: str | None
    windows: str | None


class InstallerFileNamePatterns(TypedDict):
    amd64: ArchitectureInstallerPattern
    arm64: ArchitectureInstallerPattern


class InstallerData(TypedDict):
    appName: str
    license: str
    repoURL: str
    lastCommitDate: NotRequired[str]
    lastCommitDateCheckDate: NotRequired[str]
    doc: str
    comment: NotRequired[str]
    categoryLabels: list[InstallerCategoryLabel]
    fileNamePattern: InstallerFileNamePatterns


class InstallerDataFiles(TypedDict):
    version: str
    installers: list[InstallerData]


class InstallationResultSkipped(TypedDict):
    kind: Literal["skipped"]
    appName: str
    exeName: str
    emoji: Literal["⏭️"]
    detail: str


class InstallationResultSameVersion(TypedDict):
    kind: Literal["same_version"]
    appName: str
    exeName: str
    emoji: Literal["😑"]
    version: str


class InstallationResultUpdated(TypedDict):
    kind: Literal["updated"]
    appName: str
    exeName: str
    emoji: Literal["🤩"]
    oldVersion: str
    newVersion: str


class InstallationResultFailed(TypedDict):
    kind: Literal["failed"]
    appName: str
    exeName: str
    emoji: Literal["❌"]
    error: str


InstallationResult: TypeAlias = InstallationResultSkipped | InstallationResultSameVersion | InstallationResultUpdated | InstallationResultFailed


class InstallationResultBuckets(TypedDict):
    skipped: list[InstallationResultSkipped]
    same_version: list[InstallationResultSameVersion]
    updated: list[InstallationResultUpdated]
    failed: list[InstallationResultFailed]


@dataclass(frozen=True, slots=True)
class InstallRequest:
    version: str | None
    update: bool
    user_scripts_root: Path | None


def get_os_name() -> OPERATING_SYSTEMS:
    """Get the operating system name in the format expected by the github parser."""
    sys_name = platform.system()
    match sys_name:
        case "Windows":
            return "windows"
        case "Linux":
            return "linux"
        case "Darwin":
            return "darwin"
        case _:
            raise NotImplementedError(f"System {sys_name} not supported")


def get_normalized_arch() -> CPU_ARCHITECTURES:
    """Get the normalized CPU architecture."""
    arch_raw = platform.machine().lower()
    if arch_raw in ("x86_64", "amd64"):
        return "amd64"
    if arch_raw in ("aarch64", "arm64", "armv8", "armv8l"):
        return "arm64"
    # Default to amd64 if unknown architecture
    return "amd64"
