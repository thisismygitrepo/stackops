from typing import Final, Literal

from stackops.utils.constants import STACKOPS_PYTHON_VERSION

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

# Other machines, opened from the page: SSH starts that machine's own web UI and forwards one port to it (`other_machines_links.py`).
# Switching is offered only to a browser on this machine that reached the server at one of these names: the forwarded ports listen on this
# machine's loopback, out of reach of any other browser.
LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "::1", "localhost"})
# Each machine gets one slot, found from its name: the port its tunnel listens on here and the port its web UI listens on there. A server's
# sign-in cookie is named after its own port and a browser shares cookies across the ports of one host, so two servers on the same port number
# would sign each other out. The two ranges differ so that a host sharing this machine's loopback (this machine, a WSL distribution) still
# opens, and both lie under the ports systems hand out on their own.
MACHINE_TUNNEL_PORT_BASE: Final[int] = 28420
MACHINE_REMOTE_PORT_BASE: Final[int] = 29420
MACHINE_PORT_SLOTS: Final[int] = 500
MACHINE_PORT_ATTEMPTS: Final[int] = 4
# The first start on a machine can spend a while fetching the server's two packages.
MACHINE_CONNECT_SECONDS: Final[float] = 60.0
MACHINE_CHECK_SECONDS: Final[float] = 15.0
MACHINE_OUTPUT_KEPT_BYTES: Final[int] = 16384
MACHINE_PROBLEM_LINES: Final[int] = 3
# What the page runs on another machine over SSH before it connects again (`other_machines_prepare.py`): StackOps installed where `stackops` is
# missing, with uv first where that is missing too, and updated where it is too old to be opened. Each goes inside single quotes through two
# shells, so neither may hold one. Both fetch packages, and the update also reinstalls and copies assets.
MACHINE_INSTALL_COMMAND: Final[str] = f"""command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh && uv tool install --upgrade --python {STACKOPS_PYTHON_VERSION} stackops"""
MACHINE_UPDATE_COMMAND: Final[str] = "devops self update"
MACHINE_PREPARE_SECONDS: Final[float] = 600.0
# The terminal SSH runs in. Wide, so that nothing the other machine prints is wrapped before it is read here.
MACHINE_TERMINAL_ROWS: Final[int] = 24
MACHINE_TERMINAL_COLUMNS: Final[int] = 200
# SSH signs in without a prompt or fails: this server has no terminal to ask in. The keep-alive ends a tunnel whose machine went away.
# Three options undo what a person's SSH config may set for a host, each of which would break the connection made here: a shared connection
# would keep the tunnel open after this one ends, a preset remote command refuses the one given here, and a forward of their own whose port
# is in use would end the connection. Whether the forward made here works is checked by asking the other machine through it.
MACHINE_SSH_OPTIONS: Final[tuple[str, ...]] = (
    "BatchMode=yes",
    "ConnectTimeout=10",
    "ServerAliveInterval=15",
    "ServerAliveCountMax=3",
    "ControlPath=none",
    "RemoteCommand=none",
    "ExitOnForwardFailure=no",
)
# A command over SSH gets a bare PATH, without what the shell profile adds; these are where `stackops` and `uv` are installed.
MACHINE_REMOTE_PATH: Final[str] = "$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
# Tells a web UI which machine and address it was opened from. Its page then offers the way back and no other machines.
MACHINE_OPENED_FROM_VARIABLE: Final[str] = "STACKOPS_WEBUI_OPENED_FROM"
# The only kind of name the page offers and SSH is given: no pattern, no option, no user or port.
MACHINE_NAME_PATTERN: Final[str] = r"[A-Za-z0-9][A-Za-z0-9._-]*"
MACHINE_HOME_ADDRESS_PATTERN: Final[str] = r"http://[A-Za-z0-9.\[\]:-]+/"
# Entries of the SSH config that are there for git, not to work on: those with `User git` and these hosts.
SSH_GIT_HOSTS: Final[tuple[str, ...]] = ("github.com", "gitlab.com", "bitbucket.org", "ssh.dev.azure.com")
SSH_CONFIG_INCLUDE_DEPTH: Final[int] = 8

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

# How much of a secret's value the Vault page is sent. Partly shown is a few characters at each end around a fixed run of dots, so the length is
# not given away; each end is a sixth of the text and at most the limit, which leaves a short value fully covered.
type VaultReveal = Literal["hidden", "partial", "full"]
VAULT_MASK: Final[str] = "•" * 8
VAULT_PARTIAL_EDGE_LIMIT: Final[int] = 4
VAULT_PARTIAL_EDGE_SHARE: Final[int] = 6

# The Scripts page says what a script does with its first comment or docstring line, looked for in this much of the start of the file.
SCRIPT_SUMMARY_READ_BYTES: Final[int] = 4096
SCRIPT_SUMMARY_LIMIT: Final[int] = 200
# Comments that speak to a tool and not to a person, by how they start once the comment mark is gone. They are never taken as what a script does.
SCRIPT_DIRECTIVE_PREFIXES: Final[tuple[str, ...]] = ("!", "-*-", "coding", "vim:", "type:", "pylint:", "pyright:", "mypy:", "ruff:", "noqa", "flake8:", "shellcheck ")
# What a script made by the page starts as, by the file ending of each kind it makes.
SCRIPT_STARTERS: Final[dict[str, str]] = {
    ".py": """# {summary}

print("Hello from {name}")
""",
    ".sh": """#!/usr/bin/env bash
# {summary}

echo "Hello from {name}"
""",
    ".ps1": """# {summary}

Write-Output "Hello from {name}"
""",
    ".bat": """@echo off
REM {summary}

echo Hello from {name}
""",
}
SCRIPT_STARTER_SUMMARY: Final[str] = "Say here, in one line, what this script does. The Scripts page shows it in its list."
# The parts of a new script's name: a slash between them puts the script in a folder.
SCRIPT_NAME_PATTERN: Final[str] = r"[A-Za-z0-9_][A-Za-z0-9._-]*(/[A-Za-z0-9_][A-Za-z0-9._-]*)*"
# Scripts that are not on this machine: they are fetched from the StackOps repository when one is run.
ONLINE_SCRIPTS_RAW_ROOT: Final[str] = "https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/jobs/scripts_dynamic"
# GitHub answers a machine that is not signed in sixty times an hour, and the page asks again after every finished run.
ONLINE_SCRIPTS_CACHE_SECONDS: Final[float] = 600.0
ONLINE_SCRIPT_TIMEOUT_SECONDS: Final[float] = 30.0

APP_CONTENT_SECURITY_POLICY: Final[str] = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; "
    "connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)
REPORT_CONTENT_SECURITY_POLICY: Final[str] = (
    "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; frame-ancestors 'self'"
)
