from typing import Literal, TypedDict

import psutil

from stackops.scripts.python.helpers.helpers_utils.process_models import ProcessInfo


class TerminationResult(TypedDict):
    pid: int
    name: str
    status: Literal["killed", "already_exited", "failed"]
    error: str | None


def terminate_processes(processes: list[ProcessInfo]) -> list[TerminationResult]:
    results: list[TerminationResult] = []
    for process in processes:
        result: TerminationResult = {"pid": process["pid"], "name": process["name"], "status": "killed", "error": None}
        try:
            psutil.Process(process["pid"]).kill()
        except psutil.NoSuchProcess:
            result["status"] = "already_exited"
        except psutil.Error as error:
            result["status"] = "failed"
            result["error"] = str(error)
        results.append(result)
    return results
