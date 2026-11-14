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
SYSTEM_INSTALLER_COMMANDS: Final[frozenset[str]] = frozenset(("winget", "brew", "choco", "msiexec", "msiexec.exe", "snap"))
