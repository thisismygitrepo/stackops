import json
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from stackops.jobs.installer.checks.constants import SECURITY_RECORDS_ROOT
from stackops.jobs.installer.checks.scan_history import ScanRun, list_runs, load_run
from stackops.jobs.installer.checks.scan_overview import RunSummary, Verdict, build_target_view, summarize_run
from stackops.utils.source_of_truth import LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH

# Why an app of a saved scan would or would not be installed, in the order the install command checks them (`download_safe_apps`), then the
# one thing it only finds out while installing: an app without a recorded fingerprint cannot be checked after its download.
type InstallReason = Literal["ready", "unfinished", "no_result", "check_failed", "no_verdict", "flagged", "no_copy", "no_fingerprint"]
FINISHED_STATUSES: frozenset[str] = frozenset({"completed", "completed_with_errors"})


@dataclass(frozen=True)
class ScanProblem:
    message: str
    status: int


# A saved scan as one of the choices: its summary, the names of the apps it checked (to find it by), and how many of them could be installed.
class RunChoice(RunSummary):
    apps: list[str]
    installable: int
    copies: int


class RunChoices(TypedDict):
    runs: list[RunChoice]
    folder: str


class InstallRow(TypedDict):
    name: str
    version: str | None
    file_name: str
    verdict: Verdict
    flagged_engines: int
    verdict_engines: int
    reason: InstallReason
    destination: str
    installed_at: float | None


# `whole` says the install command's own "every eligible app" picks exactly the rows marked ready, so one run of it can stand for all of them.
class InstallPlan(TypedDict):
    run: RunSummary
    folder: str
    whole: bool
    rows: list[InstallRow]


def read_saved_run(run_id: str) -> ScanRun | ScanProblem:
    try:
        return load_run(SECURITY_RECORDS_ROOT, run_id)
    except FileNotFoundError:
        return ScanProblem(message="That scan is no longer among the saved ones.", status=404)
    except (ValueError, json.JSONDecodeError, OSError) as error:
        return ScanProblem(message=f"""That scan could not be read. {error}""", status=400)


# The folder the install command puts apps in on this system, or None where it installs nothing.
def install_folder() -> Path | None:
    match platform.system().lower():
        case "linux" | "darwin":
            return Path(LINUX_INSTALL_PATH)
        case "windows":
            return Path(WINDOWS_INSTALL_PATH)
        case _:
            return None


def _install_reason(run: ScanRun, index: int) -> InstallReason:
    target = run["targets"][index]
    record = target["record"]
    if run["status"] not in FINISHED_STATUSES:
        return "unfinished"
    if record is None:
        return "no_result"
    app = record["app_data"]
    if app["positive_pct"] is None:
        return "check_failed"
    if app["verdict_engines"] == 0:
        return "no_verdict"
    if app["positive_pct"] != 0.0:
        return "flagged"
    if not app["app_url"]:
        return "no_copy"
    return "ready" if target["sha256"] else "no_fingerprint"


# When the file at an app's place was last written or put there, or None when nothing is there. The download keeps the time the cloud copy was
# made, so the time the file was moved into place is read too: that is what tells an install that just ran from a file that was there before.
def _placed_at(destination: Path | None) -> float | None:
    if destination is None or not destination.is_file():
        return None
    found = destination.stat()
    return max(found.st_mtime, found.st_ctime)


def read_run_choices() -> RunChoices:
    folder = install_folder()
    runs: list[RunChoice] = []
    for run in list_runs(SECURITY_RECORDS_ROOT):
        reasons = [_install_reason(run, index) for index in range(len(run["targets"]))]
        copies = sum(1 for target in run["targets"] if target["record"] is not None and target["record"]["app_data"]["app_url"])
        apps = sorted({build_target_view(run, index)["name"] for index in range(len(run["targets"]))}, key=str.casefold)
        runs.append({**summarize_run(run), "apps": apps, "installable": reasons.count("ready"), "copies": copies})
    return {"runs": runs, "folder": "" if folder is None else str(folder)}


def read_install_plan(run_id: str) -> InstallPlan | ScanProblem:
    run = read_saved_run(run_id)
    match run:
        case ScanProblem():
            return run
        case _:
            pass
    folder = install_folder()
    rows: list[InstallRow] = []
    for index, target in enumerate(run["targets"]):
        view = build_target_view(run, index)
        file_name = Path(target["path"]).name
        destination = None if folder is None else folder / file_name
        rows.append(
            {
                "name": view["name"],
                "version": view["version"],
                "file_name": file_name,
                "verdict": view["verdict"],
                "flagged_engines": view["flagged_engines"],
                "verdict_engines": view["verdict_engines"],
                "reason": _install_reason(run, index),
                "destination": "" if destination is None else str(destination),
                "installed_at": _placed_at(destination),
            }
        )
    return {
        "run": summarize_run(run),
        "folder": "" if folder is None else str(folder),
        "whole": all(row["reason"] != "no_fingerprint" for row in rows),
        "rows": sorted(rows, key=lambda row: (row["reason"] != "ready", row["name"].casefold())),
    }
