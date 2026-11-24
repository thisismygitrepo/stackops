import os
import time
from datetime import UTC, datetime
from typing import Final, Literal, TypedDict, cast

import psutil

from stackops.scripts.python.helpers.helpers_utils.process_models import ProcessInfo
from stackops.scripts.python.helpers.helpers_utils.process_termination import kill_scanned_process
from stackops.scripts.python.helpers.helpers_webui.machine_processes_detail import ProcessProblem

# How long the answer waits to see the processes go. One asked to quit may save its work first; one that is forced goes at once.
QUIT_WAIT_SECONDS: Final[float] = 2.5
FORCE_WAIT_SECONDS: Final[float] = 1.0
POLL_SECONDS: Final[float] = 0.1

type StopOutcome = Literal["stopped", "still_running", "already_gone", "not_allowed", "failed"]


class StopTarget(TypedDict):
    pid: int
    started: float


class StopRequest(TypedDict):
    targets: list[StopTarget]
    force: bool


class StopResult(TypedDict):
    pid: int
    started: float
    outcome: StopOutcome
    error: str | None


def parse_stop_request(body: object) -> StopRequest | ProcessProblem:
    payload = cast(dict[str, object], body) if isinstance(body, dict) else {}
    force = payload.get("force")
    listed = payload.get("targets")
    if not isinstance(force, bool) or not isinstance(listed, list) or len(cast(list[object], listed)) == 0:
        return ProcessProblem(status=400, message="Send `targets` as a list of processes and `force` as true or false.")
    targets: list[StopTarget] = []
    for item in cast(list[object], listed):
        fields = cast(dict[str, object], item) if isinstance(item, dict) else {}
        pid = fields.get("pid")
        started = fields.get("started")
        if not isinstance(pid, int) or isinstance(pid, bool) or pid < 1 or not isinstance(started, int | float) or isinstance(started, bool):
            return ProcessProblem(status=400, message="Each target needs `pid`, a process ID, and `started`, its start time.")
        targets.append({"pid": pid, "started": float(started)})
    return {"targets": targets, "force": force}


# A process that has ended can stay listed until the program that started it collects it. It counts as gone.
def has_ended(target: StopTarget) -> bool:
    try:
        process = psutil.Process(target["pid"])
        return process.create_time() != target["started"] or process.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return True


def signal_process(target: StopTarget, force: bool) -> None:
    process = psutil.Process(target["pid"])
    if process.create_time() != target["started"] or process.status() == psutil.STATUS_ZOMBIE:
        raise psutil.NoSuchProcess(target["pid"])
    if force:
        # The CLI's own kill, which checks the process against the scan it was picked from. Here that scan is the page's, and its ID and start time are all the check reads.
        scanned: ProcessInfo = {
            "pid": target["pid"], "create_time": datetime.fromtimestamp(target["started"], UTC), "name": "", "command": "", "username": "", "cpu_percent": 0.0, "memory_usage_mb": 0.0, "status": "", "ports": [],
        }
        kill_scanned_process(scanned)
    else:
        process.terminate()


# Asks each process to quit, or ends it at once with `force`, then watches for a moment so the answer can say which ones went.
# The watching only looks: it never collects a process, so a task the server itself started is still collected by the code that runs it.
def stop_processes(request: StopRequest) -> list[StopResult]:
    # The server and what it runs inside go last, so everything else has been dealt with before the server can no longer answer.
    hosts = {os.getpid(), *(parent.pid for parent in psutil.Process().parents())}
    results: list[StopResult] = []
    for target in sorted(request["targets"], key=lambda target: target["pid"] in hosts):
        result: StopResult = {"pid": target["pid"], "started": target["started"], "outcome": "still_running", "error": None}
        try:
            signal_process(target=target, force=request["force"])
        except psutil.NoSuchProcess:
            result["outcome"] = "already_gone"
        except psutil.AccessDenied:
            result["outcome"] = "not_allowed"
        except psutil.Error as error:
            result["outcome"] = "failed"
            result["error"] = str(error)
        results.append(result)
    deadline = time.monotonic() + (FORCE_WAIT_SECONDS if request["force"] else QUIT_WAIT_SECONDS)
    while True:
        waiting = [result for result in results if result["outcome"] == "still_running"]
        for result in waiting:
            if has_ended({"pid": result["pid"], "started": result["started"]}):
                result["outcome"] = "stopped"
        if all(result["outcome"] == "stopped" for result in waiting) or time.monotonic() >= deadline:
            return results
        time.sleep(POLL_SECONDS)
