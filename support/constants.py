from pathlib import Path
from typing import Final


DOTFILES_LLM_CREDENTIALS_RELATIVE_PATH: Final[Path] = Path("dotfiles", "creds", "llm")
PRIVATE_CREDENTIAL_FILE_MODE: Final[int] = 0o600

