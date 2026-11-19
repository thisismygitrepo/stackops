from typing import Final

SERVER_RUNTIME_DEPENDENCIES: Final[tuple[str, ...]] = ("starlette", "uvicorn")
WINDOWS_PTY_DEPENDENCY: Final[str] = "pywinpty"

DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8420
TOKEN_COOKIE_PREFIX: Final[str] = "stackops_serve_token"
PORT_PROBE_SECONDS: Final[float] = 1.0
LAUNCH_PATH_VARIABLE: Final[str] = "STACKOPS_SERVE_LAUNCH_PATH"
LAUNCH_VIRTUAL_ENV_VARIABLE: Final[str] = "STACKOPS_SERVE_LAUNCH_VIRTUAL_ENV"

MIN_TERMINAL_CELLS: Final[int] = 2
MAX_TERMINAL_CELLS: Final[int] = 1000
PATH_SUGGESTION_LIMIT: Final[int] = 40
# Parameters the CLI types as plain text that take a local file or folder; the form offers path suggestions for them and still accepts any text.
LOCAL_PATH_PARAMETER_NAMES: Final[frozenset[str]] = frozenset({"path", "path_local", "file_path", "directory"})
SCROLLBACK_LIMIT_BYTES: Final[int] = 4 * 1024 * 1024
# Finished runs beyond this many are forgotten, oldest first, each time a run starts; each one can hold a full scrollback.
FINISHED_RUNS_KEPT: Final[int] = 20
# Leaves the alternate screen and turns off mouse reporting and bracketed paste, which a full-screen program leaves on when it is killed.
# Leaving the alternate screen also restores the saved cursor, so the cursor is saved first: otherwise a run that never entered it jumps back to the top.
TERMINAL_RESTORE_SEQUENCE: Final[str] = "\x1b7\x1b[?1049l\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?2004l\x1b[0m"
PTY_READ_CHUNK_BYTES: Final[int] = 65536
PTY_POLL_SECONDS: Final[float] = 0.2
STOP_GRACE_SECONDS: Final[float] = 3.0
SHUTDOWN_JOIN_SECONDS: Final[float] = 2.0
# How long a stopping server waits for requests in flight before it cancels them; a cancelled capture kills its command.
GRACEFUL_SHUTDOWN_SECONDS: Final[int] = 3

CAPTURE_TIMEOUT_SECONDS: Final[float] = 90.0
CAPTURE_OUTPUT_COLUMNS: Final[int] = 118
# The largest file the app view opens to read or edit in the browser.
MAX_EDITABLE_FILE_BYTES: Final[int] = 1024 * 1024

VENDOR_DOWNLOAD_TIMEOUT_SECONDS: Final[float] = 120.0
VENDOR_CACHE_FOLDER: Final[str] = "serve-vendor"

APP_CONTENT_SECURITY_POLICY: Final[str] = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; "
    "connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)
REPORT_CONTENT_SECURITY_POLICY: Final[str] = (
    "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; frame-ancestors 'self'"
)
