from pathlib import Path
from typing import Final


DOTFILES_LLM_CREDENTIALS_RELATIVE_PATH: Final[Path] = Path("dotfiles", "creds", "llm")
PRIVATE_CREDENTIAL_FILE_MODE: Final[int] = 0o600
AUTOMATIC_PROFILE_NAME_PREFIX: Final[str] = "account"
AUTOMATIC_PROFILE_FINGERPRINT_LENGTH: Final[int] = 16
TEMPORARY_PROFILE_NAME_PREFIX: Final[str] = ".account-backup-"
