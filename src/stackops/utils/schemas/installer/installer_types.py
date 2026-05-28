import platform
from dataclasses import dataclass
from typing import Literal, NotRequired, TypeAlias, TypedDict


CPU_ARCHITECTURES: TypeAlias = Literal["amd64", "arm64"]
OPERATING_SYSTEMS: TypeAlias = Literal["windows", "linux", "darwin"]
InstallerCategoryLabel: TypeAlias = Literal[
    "ai-agents-assistants",
    "browsers-web-access",
    "build-devops-containers",
    "cloud-saas",
    "data-format-tools",
    "databases",
    "documents-markdown-latex",
    "editors-ides",
    "email-communications",
    "file-managers",
    "file-operations-archives",
    "file-transfer-sharing",
    "finance-markets",
    "graphics-images-ocr-diagrams",
    "languages-runtimes",
    "media-audio-video",
    "monitoring-performance",
    "networking-diagnostics",
    "presentations-recording",
    "productivity-knowledge",
    "qr-mobile-device-tools",
    "search-navigation",
    "security-credentials-privacy",
    "storage-backup-sync",
    "system-setup",
    "terminal-fun-visuals",
    "terminal-workspaces",
    "terminals-shells",
    "tunnels-remote-access",
    "version-control",
    "web-scraping-conversion",
    "windows-platform",
]


InstallerData = TypedDict(
    "InstallerData",
    {
        "appName": str,
        "license": str,
        "doc": str,
        "repoURL": str,
        "categoryLabels": list[InstallerCategoryLabel],
        "fileNamePattern": dict[CPU_ARCHITECTURES, dict[OPERATING_SYSTEMS, str | None]],
    },
)


InstallerDataFiles = TypedDict(
    "InstallerDataFiles",
    {
        "$schema": NotRequired[str],
        "version": str,
        "installers": list[InstallerData],
    },
)


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


InstallationResult: TypeAlias = (
    InstallationResultSkipped
    | InstallationResultSameVersion
    | InstallationResultUpdated
    | InstallationResultFailed
)


class InstallationResultBuckets(TypedDict):
    skipped: list[InstallationResultSkipped]
    same_version: list[InstallationResultSameVersion]
    updated: list[InstallationResultUpdated]
    failed: list[InstallationResultFailed]


@dataclass(frozen=True, slots=True)
class InstallRequest:
    version: str | None
    update: bool


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
