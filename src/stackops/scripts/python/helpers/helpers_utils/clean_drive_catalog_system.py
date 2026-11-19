from functools import partial
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import (
    ALL_PLATFORMS,
    BLEACHBIT_INSTALL_HINT,
    BLEACHBIT_PLATFORMS,
    STACKOPS_TEMP_PATTERNS,
    STALE_TEMP_DAYS,
)
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import CleanCategory, CleanTarget, CommandCleanup, PathCleanup, PathGlob, ToolWithPathFallback
from stackops.scripts.python.helpers.helpers_utils.clean_drive_plans import plan_bleachbit, plan_brew, plan_docker, plan_from_globs, plan_journal


CONTAINER_TARGETS: tuple[CleanTarget, ...] = (
    CleanTarget(
        key="docker-stopped-containers", title="Docker stopped containers", category=CleanCategory.CONTAINERS, risk="caution",
        note="Stopped containers and their writable layers. Runs `docker container prune --force`; cleaning it first frees more images and volumes.",
        actions={platform: CommandCleanup(
            tool="docker", install_hint=None, requires_root=False,
            plan=partial(plan_docker, kind="Containers", clean=("docker", "container", "prune", "--force")),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="docker-unused-images", title="Docker images without containers", category=CleanCategory.CONTAINERS, risk="caution",
        note="Every image no container uses; they are pulled or rebuilt again when needed. Runs `docker image prune --all --force`.",
        actions={platform: CommandCleanup(
            tool="docker", install_hint=None, requires_root=False,
            plan=partial(plan_docker, kind="Images", clean=("docker", "image", "prune", "--all", "--force")),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="docker-build-cache", title="Docker build cache", category=CleanCategory.CONTAINERS, risk="safe",
        note="BuildKit layers; the next build is slower. Runs `docker builder prune --all --force`.",
        actions={platform: CommandCleanup(
            tool="docker", install_hint=None, requires_root=False,
            plan=partial(plan_docker, kind="Build Cache", clean=("docker", "builder", "prune", "--all", "--force")),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="docker-unused-volumes", title="Docker volumes without containers", category=CleanCategory.CONTAINERS, risk="danger",
        note="Named and anonymous volumes no container uses. Their data (databases, uploads) is gone for good. Runs `docker volume prune --all --force`.",
        actions={platform: CommandCleanup(
            tool="docker", install_hint=None, requires_root=False,
            plan=partial(plan_docker, kind="Local Volumes", clean=("docker", "volume", "prune", "--all", "--force")),
        ) for platform in ALL_PLATFORMS},
    ),
)

TRASH_TARGETS: tuple[CleanTarget, ...] = (
    CleanTarget(
        key="trash", title="Trash / Recycle Bin", category=CleanCategory.TRASH, risk="caution",
        note="Files you already deleted. Emptying is permanent. BleachBit on Linux (only $XDG_DATA_HOME/Trash without it) and Windows; ~/.Trash on macOS.",
        actions={
            "linux": ToolWithPathFallback(
                tool=CommandCleanup(
                    tool="bleachbit", install_hint=BLEACHBIT_INSTALL_HINT, requires_root=False,
                    plan=partial(plan_bleachbit, executable="bleachbit", options=("system.trash",)),
                ),
                fallback=PathCleanup(
                    globs=(PathGlob("xdg_data", "Trash/files/*"), PathGlob("xdg_data", "Trash/info/*"), PathGlob("xdg_data", "Trash/expunged/*")),
                    excluded_globs=(), min_age_days=None, requires_root=False,
                ),
            ),
            "windows": CommandCleanup(
                tool="bleachbit_console", install_hint=BLEACHBIT_INSTALL_HINT, requires_root=False,
                plan=partial(plan_bleachbit, executable="bleachbit_console", options=("system.recycle_bin",)),
            ),
            "darwin": PathCleanup(globs=(PathGlob("home", ".Trash/*"),), excluded_globs=(), min_age_days=None, requires_root=False),
        },
    ),
)

SYSTEM_TARGETS: tuple[CleanTarget, ...] = (
    CleanTarget(
        key="temp-files", title="Temporary files", category=CleanCategory.SYSTEM, risk="caution",
        note=f"""BleachBit `system.tmp` on Linux and Windows: every file of yours in the temp folders that no process holds open, of any age, so finish temp work first. On macOS, $TMPDIR entries untouched for {STALE_TEMP_DAYS} days.""",
        actions={
            **{platform: CommandCleanup(
                tool=executable, install_hint=BLEACHBIT_INSTALL_HINT, requires_root=False,
                plan=partial(plan_bleachbit, executable=executable, options=("system.tmp",)),
            ) for platform, executable in BLEACHBIT_PLATFORMS.items()},
            "darwin": PathCleanup(
                globs=(PathGlob("temp", "*"),), excluded_globs=tuple(PathGlob("temp", Path(pattern).parts[0]) for pattern in STACKOPS_TEMP_PATTERNS),
                min_age_days=STALE_TEMP_DAYS, requires_root=False,
            ),
        },
    ),
    CleanTarget(
        key="thumbnails", title="Thumbnail cache", category=CleanCategory.SYSTEM, risk="safe",
        note="File-manager thumbnails, regenerated when folders are opened. BleachBit `thumbnails.cache`.",
        actions={"linux": CommandCleanup(
            tool="bleachbit", install_hint=BLEACHBIT_INSTALL_HINT, requires_root=False,
            plan=partial(plan_bleachbit, executable="bleachbit", options=("thumbnails.cache",)),
        )},
    ),
    CleanTarget(
        key="browser-caches", title="Web browser caches", category=CleanCategory.SYSTEM, risk="safe",
        note="Chrome, Chromium, Brave, Edge, Firefox and Opera caches (not cookies or history). Close the browsers first. BleachBit `*.cache`.",
        actions={platform: CommandCleanup(
            tool=executable, install_hint=BLEACHBIT_INSTALL_HINT, requires_root=False,
            plan=partial(plan_bleachbit, executable=executable, options=(
                "google_chrome.cache", "chromium.cache", "brave.cache", "microsoft_edge.cache", "firefox.cache", "opera.cache",
            )),
        ) for platform, executable in BLEACHBIT_PLATFORMS.items()},
    ),
    CleanTarget(
        key="systemd-journal", title="systemd journal", category=CleanCategory.SYSTEM, risk="caution",
        note="Old system logs; the most recent ones are kept. Runs `journalctl --vacuum-size`.",
        actions={"linux": CommandCleanup(tool="journalctl", install_hint=None, requires_root=True, plan=plan_journal)},
    ),
    CleanTarget(
        key="apt-cache", title="APT downloaded packages", category=CleanCategory.SYSTEM, risk="safe",
        note="Downloaded .deb files of installed or removed packages. Runs `apt-get clean`.",
        actions={"linux": CommandCleanup(
            tool="apt-get", install_hint=None, requires_root=True,
            plan=partial(plan_from_globs, globs=(PathGlob("filesystem_root", "var/cache/apt/archives/*.deb"), PathGlob("filesystem_root", "var/cache/apt/*.bin")), clean=("apt-get", "clean")),
        )},
    ),
    CleanTarget(
        key="snap-old-revisions", title="Disabled snap revisions", category=CleanCategory.SYSTEM, risk="caution",
        note="Older snap revisions kept for rollback. BleachBit `snap.disabled`.",
        actions={"linux": CommandCleanup(
            tool="bleachbit", install_hint=BLEACHBIT_INSTALL_HINT, requires_root=True,
            plan=partial(plan_bleachbit, executable="bleachbit", options=("snap.disabled",)),
        )},
    ),
    CleanTarget(
        key="homebrew-cleanup", title="Homebrew downloads and old versions", category=CleanCategory.SYSTEM, risk="safe",
        note="Cached downloads and outdated keg versions. Runs `brew cleanup --prune=all -s`.",
        actions={platform: CommandCleanup(tool="brew", install_hint=None, requires_root=False, plan=plan_brew) for platform in ("linux", "darwin")},
    ),
    CleanTarget(
        key="xcode-derived-data", title="Xcode DerivedData", category=CleanCategory.SYSTEM, risk="safe",
        note="Build products and indexes Xcode regenerates.",
        actions={"darwin": PathCleanup(globs=(PathGlob("home", "Library/Developer/Xcode/DerivedData/*"),), excluded_globs=(), min_age_days=None, requires_root=False)},
    ),
    CleanTarget(
        key="xcode-device-support", title="Xcode device support files", category=CleanCategory.SYSTEM, risk="caution",
        note="Debug symbols copied from devices; Xcode copies them again when that device reconnects.",
        actions={"darwin": PathCleanup(
            globs=(PathGlob("home", "Library/Developer/Xcode/iOS DeviceSupport/*"), PathGlob("home", "Library/Developer/Xcode/watchOS DeviceSupport/*")),
            excluded_globs=(), min_age_days=None, requires_root=False,
        )},
    ),
    CleanTarget(
        key="windows-update-cache", title="Windows Update download cache", category=CleanCategory.SYSTEM, risk="safe",
        note="Already-installed update payloads in SoftwareDistribution\\Download. Needs an elevated terminal.",
        actions={"windows": PathCleanup(globs=(PathGlob("system_root", "SoftwareDistribution/Download/*"),), excluded_globs=(), min_age_days=None, requires_root=True)},
    ),
)
