from dataclasses import dataclass
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_utils.autostart_common import AutostartCategory, AutostartScope

# `systemd` is a unit of the person's own service manager on Linux. `sign_in` is a program that is only opened at sign-in: a desktop file in
# the person's autostart folder on Linux, a value under their Run key or a file in their Startup folder on Windows. `listed` is everything
# else on those two systems, as the command lists it.
type EntryKind = Literal["launchd", "login_item", "systemd", "sign_in", "listed"]
type Whose = Literal["yours", "apps", "system"]
type StartManner = Literal["always", "timer", "demand"]
type LiveState = Literal["running", "waiting", "idle", "unknown"]
type EntryAction = Literal["turn_off", "turn_on", "remove"]
type ProblemReason = Literal["unsupported", "failed", "unknown_entry", "refused"]
# Why an entry has no switch: it is part of the system, it starts for every account so changing it takes an administrator, it belongs to the
# computer's security or device management, the system does not say where it is, or it is of a kind with no off switch to use.
type LockReason = Literal["", "system", "administrator", "managed", "unlocated", "no_switch"]


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
    lock: LockReason


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
