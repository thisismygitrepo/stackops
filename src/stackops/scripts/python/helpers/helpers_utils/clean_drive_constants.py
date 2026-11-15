from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import Platform, Risk


ALL_PLATFORMS: tuple[Platform, ...] = ("linux", "darwin", "windows")
BLEACHBIT_PLATFORMS: dict[Platform, str] = {"linux": "bleachbit", "windows": "bleachbit_console"}
BLEACHBIT_INSTALL_HINT = "install BleachBit from your distro (e.g. `sudo apt install bleachbit`) or bleachbit.org on Windows"
RISK_ORDER: dict[Risk, int] = {"safe": 0, "caution": 1, "danger": 2}
QUERY_TIMEOUT_SECONDS = 300
SCAN_WORKERS = 8
JOURNAL_RETAIN_MEBIBYTES = 500
STALE_TEMP_DAYS = 3
MIN_REMOVABLE_PATH_PARTS = 3
PREVIEW_PATH_LIMIT = 40
PICKER_PREVIEW_PERCENT = 55
PROJECT_SCAN_PRUNED_DIRECTORIES = frozenset({"node_modules"})
PROJECT_SCAN_PRUNED_HOME_DIRECTORIES = frozenset({"AppData", "Library", "snap", "go"})
