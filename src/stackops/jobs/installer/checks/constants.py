VT_ANALYSIS_TIMEOUT_SECONDS: float = 600.0
VT_POLL_INTERVAL_SECONDS: float = 15.0
VT_REQUEST_TIMEOUT_SECONDS: int = 60
VT_ACCOUNT_REQUEST_INTERVAL_SECONDS: float = 15.0
VT_REQUEST_ATTEMPTS_PER_ACCOUNT: int = 3
VT_RETRY_DELAY_SECONDS: float = 1.0
VT_QUOTA_RETRY_DELAY_SECONDS: float = 30.0
VT_LOCK_POLL_INTERVAL_SECONDS: float = 0.25

SCAN_HELP: str = (
    """<s> Scan installed apps or a single file path with VirusTotal.

"""
    """Automatically uses configured VirusTotal accounts. --concurrency controls parallel files and defaults to the """
    """configured account count. Requests are serialized and spaced at least 15 seconds apart per account. """
    """Temporary failures receive bounded retries; inactive or invalid accounts are disabled and requests switch """
    """to another available account. --path uses the same retry and account-switching rules. Existing reports are """
    """retrieved by SHA256 with their original analysis date; unknown files are submitted for analysis. """
    """The final report includes request and failure statistics by account name, without API keys. """
    """Scan failures are reported explicitly and cause a nonzero exit."""
)
