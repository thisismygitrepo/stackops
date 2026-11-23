from typing import Final, Literal

# Fixed sets of keywords a command takes as text and checks after it starts (`field_choice_keywords.py`).
type KeywordChoiceSource = Literal["config_agents", "mcp_agents", "doctor_agent", "doctor_resources", "reset_resources", "agent_states", "type_check_tools"]
type FieldChoiceSource = (
    Literal[
        "default_cloud", "any_cloud", "backup_entries", "backup_subset_entries", "operating_systems", "projects", "browser_profiles", "browser_profile", "dotfile_groups"
    ]
    | KeywordChoiceSource
)

SERVER_RUNTIME_DEPENDENCIES: Final[tuple[str, ...]] = ("starlette", "uvicorn")
WINDOWS_PTY_DEPENDENCY: Final[str] = "pywinpty"

DEFAULT_HOST: Final[str] = "127.0.0.1"
DEFAULT_PORT: Final[int] = 8420
TOKEN_COOKIE_PREFIX: Final[str] = "stackops_webui_token"
PORT_PROBE_SECONDS: Final[float] = 1.0
LAUNCH_PATH_VARIABLE: Final[str] = "STACKOPS_WEBUI_LAUNCH_PATH"
LAUNCH_VIRTUAL_ENV_VARIABLE: Final[str] = "STACKOPS_WEBUI_LAUNCH_VIRTUAL_ENV"

MIN_TERMINAL_CELLS: Final[int] = 2
MAX_TERMINAL_CELLS: Final[int] = 1000
PATH_SUGGESTION_LIMIT: Final[int] = 40
# Parameters the CLI types as plain text that take a local file or folder; both views' forms offer path suggestions for them and still accept any text.
# `root`, `source` and `target` are left out: in some tools they are remote.
LOCAL_PATH_PARAMETER_NAMES: Final[frozenset[str]] = frozenset(
    {
        "path",
        "path_local",
        "file_path",
        "directory",
        "pdf_input",
        "data_path",
        "output",
        "output_dir",
        "output_path",
        "repo",
        "find_root",
        "search_root",
        "project_path",
        "context_path",
        "prompt_path",
        "agents_dir",
        "agent_dir",
        "input_path",
        "file",
    }
)
# Parameters the CLI takes as plain text although their valid values are a list this machine can read in milliseconds, or a fixed set of keywords
# the command checks after it starts. The app view's form offers that list in place of the text box (`field_choices.py`); the CLI and the developer
# view stay as they are. Keyed by command path, then parameter name. A list may follow one other field of the same command (a browser's profiles).
# Left out on purpose: lists that need the network, a disk scan or a running program, names kept in the secrets file, and fields that name
# something being made (a new group, the target of a copy).
FIELD_CHOICE_SOURCES: Final[dict[str, dict[str, FieldChoiceSource]]] = {
    "devops data sync": {"cloud": "default_cloud", "which": "backup_entries"},
    "devops data subset": {"which": "backup_subset_entries"},
    "devops data register": {"os": "operating_systems"},
    "devops repos register": {"cloud": "default_cloud"},
    "devops repos guard": {"cloud": "default_cloud"},
    "devops repos sync": {"which": "projects"},
    "devops config setup cloud": {"cloud": "any_cloud"},
    "devops config dotfiles register": {"os_filter": "operating_systems"},
    "devops config dotfiles status": {"which": "dotfile_groups"},
    "cloud mount": {"clouds": "any_cloud"},
    "cloud copy": {"record_os": "operating_systems"},
    "agents browser launch": {"profile": "browser_profiles"},
    "agents browser close": {"profile": "browser_profiles"},
    "agents browser declutter": {"profile": "browser_profile"},
    "agents init": {"agent": "config_agents"},
    "agents add-mcp": {"agents": "mcp_agents"},
    "agents doctor": {"agent": "doctor_agent", "resource": "doctor_resources"},
    "agents reset": {"agent": "doctor_agent", "resource": "reset_resources"},
    "agents status": {"state": "agent_states"},
    "utils pyproject type-check": {"tools": "type_check_tools"},
}
OPERATING_SYSTEM_TITLES: Final[dict[str, str]] = {"linux": "Linux", "darwin": "macOS", "windows": "Windows"}
# The word the CLI takes for every entry of a list at once.
EVERY_ITEM_CHOICE: Final[str] = "all"
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

# An app that does not answer `--version` this fast is treated as having no readable version.
VERSION_PROBE_TIMEOUT_SECONDS: Final[float] = 5.0
GITHUB_RELEASE_TIMEOUT_SECONDS: Final[float] = 30.0
# How long a repository's latest release is remembered, so checking again after an update only reads the installed versions.
GITHUB_RELEASE_CACHE_SECONDS: Final[float] = 600.0

VENDOR_DOWNLOAD_TIMEOUT_SECONDS: Final[float] = 120.0
VENDOR_CACHE_FOLDER: Final[str] = "webui-vendor"

APP_CONTENT_SECURITY_POLICY: Final[str] = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; "
    "connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)
REPORT_CONTENT_SECURITY_POLICY: Final[str] = (
    "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; frame-ancestors 'self'"
)
