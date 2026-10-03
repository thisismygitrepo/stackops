from typing import Literal


type StatusSection = Literal["system", "shell", "repos", "ssh", "configs", "apps", "backup"]
type StatusLevel = Literal["ready", "attention", "error"]

ALL_STATUS_SECTIONS: tuple[StatusSection, ...] = ("apps", "repos", "backup", "configs", "system", "shell", "ssh")
STATUS_TITLES: dict[StatusSection, str] = {
    "system": "Machine",
    "shell": "Shell profile",
    "repos": "Repositories",
    "ssh": "SSH",
    "configs": "Configuration files",
    "apps": "Apps installed",
    "backup": "Data",
}
STATUS_STYLES: dict[StatusLevel, str] = {"ready": "green", "attention": "yellow", "error": "red"}
COMPACT_WIDTH = 90
