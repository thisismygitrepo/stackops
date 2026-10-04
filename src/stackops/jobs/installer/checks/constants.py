DEFAULT_APPS_PER_KEY: int = 1

SCAN_HELP: str = (
    """<s> Scan installed apps or a single file path with VirusTotal.

"""
    """Automatically uses configured VirusTotal API keys. --apps-per-key controls concurrent apps per key (default: 1), """
    """with one API request at a time per key. Maximum parallel apps = min(file count, key count x apps per key); """
    """--path scans one file with one key. Available keys, keys in use, configured apps per key, and maximum parallel apps """
    """are shown at scan startup."""
)
