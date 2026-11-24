from typing import Final

# A folder's size is counted over this many files at most; past it the page says "more than".
FOLDER_MEASURE_LIMIT: Final[int] = 20000
# How much of a file's start is read to tell an encrypted file by what is in it, not by its name.
ENCRYPTED_SNIFF_BYTES: Final[int] = 8192
GPG_LIST_TIMEOUT_SECONDS: Final[float] = 10.0

# Asking the cloud itself whether it answers goes over the network, so it gives up quickly and is asked for apart from the rest.
CLOUD_REACH_TIMEOUT_SECONDS: Final[float] = 20.0
RCLONE_REACH_FLAGS: Final[tuple[str, ...]] = ("--contimeout", "6s", "--timeout", "10s", "--retries", "1", "--low-level-retries", "1")
# A file up to this size is fingerprinted for the upload preview, which makes the exact place in the cloud known before the upload.
UPLOAD_FINGERPRINT_LIMIT_BYTES: Final[int] = 64 * 1024 * 1024

DRIVE_FILE_ADDRESS: Final[str] = "https://drive.google.com/uc?export=download&id="
DRIVE_ID_PATTERN: Final[str] = r"[A-Za-z0-9_-]{10,}"
DRIVE_PROBE_TIMEOUT_SECONDS: Final[float] = 10.0
DRIVE_PROBE_READ_BYTES: Final[int] = 65536
# Where the download command puts a file: a new folder under `path_core.tmpdir`, whose root that module does not export.
DOWNLOAD_ROOT: Final[tuple[str, ...]] = ("tmp_results", "tmp_dirs")

EXPORT_FOLDER_PREFIX: Final[str] = "security-scan"
EXPORT_HOME_FOLDER: Final[str] = "Downloads"

# How much of what GPG said is passed on to the page when a run with a password fails.
LOCKER_DETAIL_LIMIT: Final[int] = 400
LOCKER_SECRET_MASK: Final[str] = "•••"
