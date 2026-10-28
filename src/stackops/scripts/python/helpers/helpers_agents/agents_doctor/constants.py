from typing import Final, Literal

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorOrigin


DOCTOR_ESTIMATED_CHARACTERS_PER_TOKEN: Final[int] = 4
DOCTOR_VERSION_TIMEOUT_SECONDS: Final[int] = 3
CLEANUP_RESOURCE_CHOICES: Final[tuple[str, ...]] = ("all", "workspace", "configuration", "mcp", "hook", "plugin", "skill", "instructions")
CLEANUP_ORIGIN_LABELS: Final[dict[DoctorOrigin, Literal["workspace", "user", "admin", "system"]]] = {
    "local": "workspace",
    "global": "user",
    "admin": "admin",
    "system": "system",
}
