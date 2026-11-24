import re
import shutil
from dataclasses import dataclass
from typing import Literal, TypedDict, cast

import psutil

from stackops.scripts.python.helpers.helpers_devops.cli_ssh_port import ensure_local_port_available
from stackops.scripts.python.helpers.helpers_webui.machine_processes_stop import StopOutcome, stop_processes
from stackops.scripts.python.helpers.helpers_webui.network_constants import FORWARD_STACKOPS_MARKS, FORWARD_SWITCHER_MARKS
from stackops.scripts.python.helpers.helpers_webui.other_machines_hosts import SshHost, read_ssh_hosts

SSH_PROCESS_NAMES = frozenset({"ssh", "ssh.exe"})
# The options of `ssh` that are followed by a value of their own, so the value is not taken for the machine's name.
SSH_VALUE_OPTIONS = frozenset("BbcDEeFIiJLlmOoPpQRSWw")
# A local forward as SSH takes it: an optional address to listen on, the port here, then the machine and port over there.
FORWARD_PATTERN = re.compile(r"(?:(\[[^\]]+\]|[^:\[\]]*):)?(\d{1,5}):(\[[^\]]+\]|[^:\[\]]+):(\d{1,5})")

# Who started a forward: the port-mapping command, this app's machine switcher (stopping one of those closes the other machine's page), or
# something else on this machine.
type ForwardOrigin = Literal["stackops", "switcher", "other"]


@dataclass(frozen=True, slots=True)
class ForwardProblem:
    status: int
    message: str


class ForwardMapping(TypedDict):
    listens_on: str
    local_port: int
    remote_host: str
    remote_port: int


# One running `ssh` that forwards ports. It is named by its process ID together with its start time, as on the Processes page.
class RunningForward(TypedDict):
    pid: int
    started: float
    destination: str
    origin: ForwardOrigin
    mappings: list[ForwardMapping]


class ForwardsOverview(TypedDict):
    ssh_installed: bool
    forwards: list[RunningForward]


class PortAnswer(TypedDict):
    port: int
    free: bool
    reason: str


class StopAnswer(TypedDict):
    outcome: StopOutcome
    error: str | None


def read_command_line(arguments: list[str]) -> tuple[str, list[ForwardMapping]]:
    mappings: list[ForwardMapping] = []
    user = ""
    destination = ""
    position = 1
    while position < len(arguments):
        argument = arguments[position]
        position += 1
        if argument == "--":
            destination = arguments[position] if position < len(arguments) else ""
            break
        if not argument.startswith("-") or len(argument) < 2:
            destination = argument
            break
        # Letters can be written together (`-NT`), and a value can follow its letter in the same word (`-L8080:db:5432`) or be the next word.
        letter = next((character for character in argument[1:] if character in SSH_VALUE_OPTIONS), "")
        if letter == "":
            continue
        value = argument[argument.index(letter) + 1 :]
        if value == "" and position < len(arguments):
            value = arguments[position]
            position += 1
        if letter == "l":
            user = value
        found = FORWARD_PATTERN.fullmatch(value) if letter == "L" else None
        if found is not None:
            mappings.append({"listens_on": (found.group(1) or "127.0.0.1").strip("[]"), "local_port": int(found.group(2)), "remote_host": found.group(3).strip("[]"), "remote_port": int(found.group(4))})
    return (f"""{user}@{destination}""" if user != "" and "@" not in destination else destination), mappings


def read_forwards() -> list[RunningForward]:
    forwards: list[RunningForward] = []
    for process in psutil.process_iter(["name"]):
        if process.info["name"] not in SSH_PROCESS_NAMES:
            continue
        try:
            arguments = process.cmdline()
            started = process.create_time()
        except psutil.Error:
            continue
        destination, mappings = read_command_line(arguments=arguments)
        if len(mappings) == 0:
            continue
        origin: ForwardOrigin = "stackops" if all(mark in arguments for mark in FORWARD_STACKOPS_MARKS) else "switcher" if all(mark in arguments for mark in FORWARD_SWITCHER_MARKS) else "other"
        forwards.append({"pid": process.pid, "started": started, "destination": destination, "origin": origin, "mappings": mappings})
    return sorted(forwards, key=lambda forward: forward["started"], reverse=True)


def read_forwards_overview() -> ForwardsOverview:
    return {"ssh_installed": shutil.which("ssh") is not None, "forwards": read_forwards()}


# The machines the SSH config names, as the machine switcher reads them. Asked for apart from the forwards: the list can run to a thousand
# names and does not change while the page is open, and the forwards are read again every few seconds.
def read_forward_hosts() -> list[SshHost]:
    return read_ssh_hosts()


# Whether a port on this machine is free to listen on, asked the way the port-mapping command asks before it starts.
def check_local_port(text: str) -> PortAnswer | ForwardProblem:
    if not text.isdecimal() or not 1 <= int(text) <= 65_535:
        return ForwardProblem(status=400, message="A port is a number between 1 and 65535.")
    port = int(text)
    try:
        ensure_local_port_available(local_port=port)
    except ValueError as error:
        return {"port": port, "free": False, "reason": "Ports under 1024 are reserved for the system." if port < 1024 and "ermission" in str(error) else "Something on this machine already uses it."}
    return {"port": port, "free": True, "reason": ""}


# Stops one forward by ending its `ssh`. The process is looked up again first, so nothing but a running forward can be stopped from here.
def stop_forward(body: object) -> StopAnswer | ForwardProblem:
    payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
    pid = payload.get("pid")
    started = payload.get("started")
    if not isinstance(pid, int) or isinstance(pid, bool) or not isinstance(started, int | float) or isinstance(started, bool):
        return ForwardProblem(status=400, message="Name the forward by `pid` and `started`.")
    if not any(forward["pid"] == pid and forward["started"] == float(started) for forward in read_forwards()):
        return {"outcome": "already_gone", "error": None}
    result = stop_processes({"targets": [{"pid": pid, "started": float(started)}], "force": False})[0]
    return {"outcome": result["outcome"], "error": result["error"]}
