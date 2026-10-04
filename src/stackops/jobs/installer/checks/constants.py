DEFAULT_APPS_PER_KEY: int = 1
VT_ANALYSIS_TIMEOUT_SECONDS: float = 600.0
VT_POLL_INTERVAL_SECONDS: float = 15.0
VT_REQUEST_TIMEOUT_SECONDS: int = 60

SCAN_HELP: str = (
    """<s> Scan installed apps or a single file path with VirusTotal.

"""
    """Automatically uses configured VirusTotal API keys. --apps-per-key controls concurrent apps per key (default: 1), """
    """with one API request at a time per key. Maximum parallel apps = min(file count, key count x apps per key); """
    """--path scans one file with one key. Available keys, keys in use, configured apps per key, and maximum parallel apps """
    """are shown at scan startup. Existing reports are retrieved by SHA256 with their original analysis date; """
    """unknown files are submitted for analysis. Scan failures are reported explicitly and cause a nonzero exit."""
)
