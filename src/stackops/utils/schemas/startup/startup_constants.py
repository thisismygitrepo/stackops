from typing import Final

from stackops.utils.schemas.startup.startup_types import StartupFileVersion, StartupKind, StartupWhen

STARTUP_FILE_VERSION: Final[StartupFileVersion] = "0.1"
STARTUP_KINDS: Final[tuple[StartupKind, ...]] = ("script", "layout")
STARTUP_WHENS: Final[tuple[StartupWhen, ...]] = ("login", "boot")
STARTUP_ENTRY_KEYS: Final[frozenset[str]] = frozenset({"kind", "name", "os", "when"})
STARTUP_SCHEMA_URL: Final[str] = "https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/utils/schemas/startup/startup.schema.json"
