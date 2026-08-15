from pathlib import Path
from typing import Final

from stackops.utils.source_of_truth import CONFIG_ROOT


INSTALLER_DATA_PATH: Final[Path] = Path(__file__).resolve().parents[1].joinpath("schemas", "installer", "installer_data.json")
COMMIT_DATE_REPORT_PATH: Final[Path] = CONFIG_ROOT.joinpath("profile", "records", "github_commit_dates.csv")
GITHUB_HOST: Final[str] = "github.com"
MAX_CONCURRENT_GITHUB_REQUESTS: Final[int] = 8
COMMIT_DATE_DISPLAY_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
COMMIT_DATE_REPORT_COLUMNS: Final[tuple[str, str]] = ("repository", "last_commit_utc")
COMMIT_DATE_EXTREME_COUNT: Final[int] = 5
NEW_OUTPUT_FILE_MODE: Final[int] = 0o600
