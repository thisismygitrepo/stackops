from typing import Final

SERVER_RUNTIME_DEPENDENCIES: Final[tuple[str, ...]] = ("starlette", "uvicorn")
WINDOWS_PTY_DEPENDENCY: Final[str] = "pywinpty"

DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8420
TOKEN_COOKIE_PREFIX: Final[str] = "stackops_serve_token"
LAUNCH_PATH_VARIABLE: Final[str] = "STACKOPS_SERVE_LAUNCH_PATH"
LAUNCH_VIRTUAL_ENV_VARIABLE: Final[str] = "STACKOPS_SERVE_LAUNCH_VIRTUAL_ENV"

MIN_TERMINAL_CELLS: Final[int] = 2
MAX_TERMINAL_CELLS: Final[int] = 1000
PATH_SUGGESTION_LIMIT: Final[int] = 40
SCROLLBACK_LIMIT_BYTES: Final[int] = 4 * 1024 * 1024
PTY_READ_CHUNK_BYTES: Final[int] = 65536
PTY_POLL_SECONDS: Final[float] = 0.2
STOP_GRACE_SECONDS: Final[float] = 3.0
SHUTDOWN_JOIN_SECONDS: Final[float] = 2.0

VENDOR_DOWNLOAD_TIMEOUT_SECONDS: Final[float] = 120.0
VENDOR_CACHE_FOLDER: Final[str] = "serve-vendor"

APP_CONTENT_SECURITY_POLICY: Final[str] = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; "
    "connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)
REPORT_CONTENT_SECURITY_POLICY: Final[str] = (
    "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; frame-ancestors 'self'"
)
