from typing import Final


WINGET_NO_APPLICABLE_UPDATE_CODES: Final[frozenset[int]] = frozenset((0x8A15002B, -1978335189))

BULK_INSTALL_PARALLEL_JOBS: Final[int] = 20
BULK_INSTALL_POLL_SECONDS: Final[float] = 0.1
BULK_INSTALL_SUDO_KEEPALIVE_SECONDS: Final[float] = 60.0
BULK_INSTALL_LOG_TAIL_BYTES: Final[int] = 8192
BULK_INSTALL_FAILURE_TAIL_LINES: Final[int] = 10
BULK_INSTALL_FAILURE_EXCERPT_COUNT: Final[int] = 5
BULK_INSTALL_SLOWEST_COUNT: Final[int] = 3
BULK_INSTALL_SUDO_EXAMPLE_COUNT: Final[int] = 4
BULK_INSTALL_VERSION_WIDTH: Final[int] = 48
# An installer that prints a line starting with this marker opens a step; a group install lists each step with its duration as it ends.
BULK_INSTALL_STEP_MARKER: Final[str] = "::step::"
# An installer prints a line starting with this marker once it is done with the system package manager. The batch then lets
# the next system installer run, and lets the ones waiting for the base system's packages start, while it finishes the rest.
BULK_INSTALL_SYSTEM_READY_MARKER: Final[str] = "::system-ready::"
# An installer prints this marker followed by a directory when it puts executables where PATH does not reach yet.
# Installers the batch starts afterwards get that directory on their PATH.
BULK_INSTALL_PATH_MARKER: Final[str] = "::path::"
# These install the tools other installers call (sudo, git, curl, unzip, bun). In a batch that has one, only installers that
# just download a release start alongside it. System installers and scripts wait for its system packages, and the other
# installers that run a command wait until it is done, as it may be installing the very tool they call.
BASE_SYSTEM_INSTALLERS: Final[frozenset[str]] = frozenset(("sysabc",))
APT_DOWNLOAD_PARALLEL_JOBS: Final[int] = 16
APT_DOWNLOAD_PACKAGES_PER_JOB: Final[int] = 4
UNINSTALL_FAILURE_TAIL_LINES: Final[int] = 5
SYSTEM_INSTALLER_COMMANDS: Final[frozenset[str]] = frozenset(("winget", "brew", "choco", "msiexec", "msiexec.exe", "snap"))
# Scripts that only download and copy files; they never call a system package manager, so they run alongside the rest of a batch.
SCRIPTS_WITHOUT_SYSTEM_INSTALLER: Final[frozenset[str]] = frozenset(("nerdfont.py",))
