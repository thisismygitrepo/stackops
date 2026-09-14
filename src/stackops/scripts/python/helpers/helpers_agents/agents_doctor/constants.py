from typing import Final


DOCTOR_ESTIMATED_CHARACTERS_PER_TOKEN: Final[int] = 4
DOCTOR_VERSION_TIMEOUT_SECONDS: Final[int] = 3
CLEANUP_RESOURCE_CHOICES: Final[tuple[str, ...]] = ("all", "workspace", "configuration", "mcp", "hook", "plugin", "skill", "instructions")
