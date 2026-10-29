from pathlib import Path
from typing import Final


CODEX_SYSTEM_ROOT: Final[Path] = Path("/etc/codex")
CODEX_HOOKS_NON_EVENT_KEYS: Final[frozenset[str]] = frozenset({"managed_dir", "windows_managed_dir", "state"})
