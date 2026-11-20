import csv
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Literal, TypedDict

from stackops.jobs.installer.checks.report_utils import get_row_status
from stackops.jobs.installer.checks.scan_history import RunScope, RunStatus, ScanRun
from stackops.jobs.installer.checks.scan_outcomes import ScanSource

type Verdict = Literal["clean", "review", "flagged", "no_verdict", "failed", "pending", "not_scanned", "unchecked"]


class TargetView(TypedDict):
    name: str
    version: str | None
    path: str
    verdict: Verdict
    positive_pct: float | None
    flagged_engines: int
    verdict_engines: int
    total_engines: int
    malicious_engines: int
    suspicious_engines: int
    harmless_engines: int
    undetected_engines: int
    checked_at: str | None
    analyzed_at: str | None
    sha256: str | None
    source: ScanSource | None
    notes: str
    app_url: str
    run_id: str | None
    target_id: int | None


class InstalledAppView(TargetView):
    changed_since: bool


class EngineView(TypedDict):
    target_id: int
    engine_name: str
    engine_category: str
    engine_result: str | None


class RunSummary(TypedDict):
    run_id: str
    started_at: str
    finished_at: str | None
    status: RunStatus
    scope: RunScope
    requested: list[str]
    hostname: str
    message: str | None
    targets: int
    counts: dict[Verdict, int]


class RunView(TypedDict):
    run: RunSummary
    targets: list[TargetView]
    engines: list[EngineView]
    accounts: list[dict[str, str]]


def build_target_view(run: ScanRun, index: int) -> TargetView:
    target = run["targets"][index]
    view: TargetView = {
        "name": Path(target["path"]).stem,
        "version": target["version"],
        "path": target["path"],
        "verdict": "pending" if run["status"] == "running" else "not_scanned",
        "positive_pct": None,
        "flagged_engines": 0,
        "verdict_engines": 0,
        "total_engines": 0,
        "malicious_engines": 0,
        "suspicious_engines": 0,
        "harmless_engines": 0,
        "undetected_engines": 0,
        "checked_at": target["checked_at"],
        "analyzed_at": None,
        "sha256": target["sha256"],
        "source": target["source"],
        "notes": "",
        "app_url": "",
        "run_id": run["run_id"],
        "target_id": index + 1,
    }
    record = target["record"]
    if record is not None:
        data = record["app_data"]
        view.update(
            name=data["app_name"],
            verdict=get_row_status(data),
            positive_pct=data["positive_pct"],
            flagged_engines=data["flagged_engines"],
            verdict_engines=data["verdict_engines"],
            total_engines=data["total_engines"],
            malicious_engines=data["malicious_engines"],
            suspicious_engines=data["suspicious_engines"],
            harmless_engines=data["harmless_engines"],
            undetected_engines=data["undetected_engines"],
            analyzed_at=data["scan_time"] or None,
            notes=data["notes"],
            app_url=data["app_url"],
        )
    return view


def summarize_run(run: ScanRun) -> RunSummary:
    counts: dict[Verdict, int] = {}
    for index in range(len(run["targets"])):
        verdict = build_target_view(run, index)["verdict"]
        counts[verdict] = counts.get(verdict, 0) + 1
    return {
        "run_id": run["run_id"],
        "started_at": run["started_at"],
        "finished_at": run["finished_at"],
        "status": run["status"],
        "scope": run["scope"],
        "requested": run["requested"],
        "hostname": run["hostname"],
        "message": run["message"],
        "targets": len(run["targets"]),
        "counts": counts,
    }


def build_run_view(run: ScanRun, app_names: set[str] | None) -> RunView:
    targets: list[TargetView] = []
    engines: list[EngineView] = []
    for index, target in enumerate(run["targets"]):
        view = build_target_view(run, index)
        if app_names is not None and view["name"].lower() not in app_names:
            continue
        targets.append(view)
        if target["record"] is not None:
            engines.extend(
                {
                    "target_id": index + 1,
                    "engine_name": engine["engine_name"],
                    "engine_category": engine["engine_category"],
                    "engine_result": engine["engine_result"],
                }
                for engine in target["record"]["engine_results"]
            )
    return {"run": summarize_run(run), "targets": targets, "engines": engines, "accounts": list(csv.DictReader(StringIO(run["account_csv"])))}


def build_overview(runs: list[ScanRun], installed: list[tuple[Path, str | None]]) -> list[InstalledAppView]:
    # `runs` is newest first. A result that carries a verdict outranks a newer attempt that failed, since a failed lookup says nothing about the file.
    latest: dict[str, TargetView] = {}
    for run in runs:
        for index, target in enumerate(run["targets"]):
            if target["record"] is None:
                continue
            known = latest.get(target["path"])
            if known is not None and known["verdict"] != "failed":
                continue
            view = build_target_view(run, index)
            if known is None or view["verdict"] != "failed":
                latest[target["path"]] = view
    apps: list[InstalledAppView] = []
    for app_path, version in installed:
        path = app_path.expanduser().absolute().as_posix()
        view = latest.get(path)
        if view is None:
            apps.append(
                {
                    "name": app_path.stem,
                    "version": version,
                    "path": path,
                    "verdict": "unchecked",
                    "positive_pct": None,
                    "flagged_engines": 0,
                    "verdict_engines": 0,
                    "total_engines": 0,
                    "malicious_engines": 0,
                    "suspicious_engines": 0,
                    "harmless_engines": 0,
                    "undetected_engines": 0,
                    "checked_at": None,
                    "analyzed_at": None,
                    "sha256": None,
                    "source": None,
                    "notes": "",
                    "app_url": "",
                    "run_id": None,
                    "target_id": None,
                    "changed_since": False,
                }
            )
            continue
        # The file is not hashed again here: one that was written or put in place after its check is reported as changed since.
        file_stat = app_path.stat()
        checked_at = view["checked_at"]
        changed_since = checked_at is not None and max(file_stat.st_mtime, file_stat.st_ctime) > datetime.fromisoformat(checked_at).timestamp()
        apps.append({**view, "version": version, "changed_since": changed_since})
    return sorted(apps, key=lambda app: (app["name"].casefold(), app["path"]))
