from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import Platform, Risk


ALL_PLATFORMS: tuple[Platform, ...] = ("linux", "darwin", "windows")
BLEACHBIT_PLATFORMS: dict[Platform, str] = {"linux": "bleachbit", "windows": "bleachbit_console"}
BLEACHBIT_INSTALL_HINT = "install BleachBit from your distro (e.g. `sudo apt install bleachbit`) or bleachbit.org on Windows"
MACOS_FULL_DISK_ACCESS_HINT = "grant your terminal app Full Disk Access in System Settings → Privacy & Security, then restart it"
RISK_ORDER: dict[Risk, int] = {"safe": 0, "caution": 1, "danger": 2}
QUERY_TIMEOUT_SECONDS = 300
SCAN_WORKERS = 8
JOURNAL_RETAIN_MEBIBYTES = 500
STALE_TEMP_DAYS = 3
MIN_REMOVABLE_PATH_PARTS = 3
PREVIEW_PATH_LIMIT = 40
DETAIL_ITEM_LIMIT = 200
PICKER_PREVIEW_PERCENT = 55
STACKOPS_SCRATCH_ENTRIES: dict[str, str] = {
    "tmp_scripts": "*/*", "sessions": "*/*", "tmp_files": "*", "tmp_dirs": "*", "tmp_installers": "*",
    "installer_logs": "*", "tmp_unzips": "*", "textual_options_form": "*", "cache": "*",
}
STACKOPS_TEMP_PATTERNS: tuple[str, ...] = (
    "stackops-browser-profiles/*/*", "stackops-python-api-graph-*", "stackops-serve-directory-*", "stackops-yazi-preview-*",
    "stackops-dmg-*", "stackops-openshell-*", "stackops-sshd-*", "stackops-zellij-*", "stackops_bulk_install_*",
    "run_shell_script_*", "seek_stdin_*", "inspect_repos_*", "agents_ask_*", "generic_instructions.md",
)
CK_INDEX_MARKER = ".lock"
GREPAI_OLLAMA_MODEL = "nomic-embed-text"
SEMTOOLS_HUB_MODEL = "hub/models--minishlab--potion-multilingual-128M"
PROJECT_SCAN_PRUNED_DIRECTORIES = frozenset({"node_modules"})
PROJECT_SCAN_PRUNED_HOME_DIRECTORIES = frozenset({"AppData", "Library", "snap", "go"})
