from dataclasses import dataclass
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_utils.autostart_common import AutostartCategory, AutostartScope

type EntryKind = Literal["launchd", "login_item", "listed"]
type Whose = Literal["yours", "apps", "system"]
type StartManner = Literal["always", "timer", "demand"]
type LiveState = Literal["running", "waiting", "idle", "unknown"]
type EntryAction = Literal["turn_off", "turn_on", "remove"]
type ProblemReason = Literal["unsupported", "failed", "unknown_entry", "refused"]


# One thing that starts on its own. `name`, `description`, `category`, `scope`, `source` and `stock` are what `utils machine autostart` prints.
# The rest is what the page adds: a readable `title`, whose it is, how it starts, what it runs, the file that defines it, and what it is doing now.
class StartupEntry(TypedDict):
    id: str
    kind: EntryKind
    name: str
    title: str
    description: str
    category: AutostartCategory
    scope: AutostartScope
    source: str
    stock: bool
    whose: Whose
    owner: str
    enabled: bool
    manner: StartManner
    triggers: list[str]
    program: str
    file: str
    live: LiveState
    pid: int | None
    last_exit: int | None
    actions: list[EntryAction]


class StartupPicture(TypedDict):
    platform: str
    entries: list[StartupEntry]
    notes: list[str]


class CalendarSlot(TypedDict):
    month: int | None
    day: int | None
    weekday: int | None
    hour: int | None
    minute: int | None


class StartupDetail(TypedDict):
    arguments: list[str]
    working_directory: str
    run_as: str
    output_files: list[str]
    calendar: list[CalendarSlot]
    watched: list[str]
    runs: int | None


class RemovedLoginItem(TypedDict):
    name: str
    path: str
    hidden: bool


@dataclass(frozen=True)
class StartupProblem:
    reason: ProblemReason
    message: str
