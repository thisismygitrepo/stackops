import json
import os
import platform
import re
import socket
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict, cast
from uuid import uuid4

from stackops.jobs.installer.checks.report_utils import ScannedAppRecord
from stackops.jobs.installer.checks.scan_outcomes import ScanSource, ScanStage

type RunScope = Literal["all", "apps", "path"]
type RunStatus = Literal["running", "completed", "completed_with_errors", "failed", "interrupted", "empty"]


class RunError(TypedDict):
    stage: ScanStage
    error_type: str
    error_code: str | None


class RunTarget(TypedDict):
    path: str
    version: str | None
    checked_at: str | None
    sha256: str | None
    source: ScanSource | None
    error: RunError | None
    record: ScannedAppRecord | None


class ScanRun(TypedDict):
    run_id: str
    started_at: str
    finished_at: str | None
    status: RunStatus
    scope: RunScope
    requested: list[str]
    hostname: str
    platform: str
    pid: int
    concurrency: int | None
    message: str | None
    targets: list[RunTarget]
    account_csv: str


def create_run(
    root: Path,
    scope: RunScope,
    requested: list[str],
    apps_to_scan: list[tuple[Path, str | None]],
    concurrency: int | None,
) -> ScanRun:
    started_at = datetime.now(UTC)
    run_id = f"""{started_at:%Y%m%dT%H%M%S%fZ}_{uuid4().hex}"""
    root.mkdir(parents=True, exist_ok=True)
    (root / run_id).mkdir()
    run: ScanRun = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "finished_at": None,
        "status": "running",
        "scope": scope,
        "requested": list(requested),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "pid": os.getpid(),
        "concurrency": concurrency,
        "message": None,
        "targets": [
            {
                "path": app_path.expanduser().absolute().as_posix(),
                "version": version,
                "checked_at": None,
                "sha256": None,
                "source": None,
                "error": None,
                "record": None,
            }
            for app_path, version in apps_to_scan
        ],
        "account_csv": "",
    }
    save_run(root, run)
    return run


def save_run(root: Path, run: ScanRun) -> None:
    run_id = run["run_id"]
    if re.fullmatch(r"\d{8}T\d{12}Z_[0-9a-f]{32}", run_id) is None:
        raise ValueError("Invalid scan run ID.")
    run_directory = root / run_id
    run_path = run_directory / "run.json"
    if run_path.exists():
        existing = cast(ScanRun, json.loads(run_path.read_text(encoding="utf-8")))
        if existing["status"] != "running" or existing["finished_at"] is not None:
            raise ValueError(f"""Scan run {run_id} is already finalized.""")
    temporary_path = run_directory / f""".run-{uuid4().hex}.tmp"""
    try:
        with temporary_path.open("x", encoding="utf-8") as output:
            json.dump(run, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        temporary_path.replace(run_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def load_run(root: Path, run_id: str | None) -> ScanRun:
    if run_id is None:
        runs = list_runs(root)
        if not runs:
            raise FileNotFoundError(f"""No saved scan runs in {root}.""")
        return runs[0]
    if re.fullmatch(r"\d{8}T\d{12}Z_[0-9a-f]{32}", run_id) is None:
        raise ValueError("Invalid scan run ID.")
    run_path = root / run_id / "run.json"
    return cast(ScanRun, json.loads(run_path.read_text(encoding="utf-8")))


def list_runs(root: Path) -> list[ScanRun]:
    runs: list[ScanRun] = []
    for run_path in root.glob("*/run.json"):
        if re.fullmatch(r"\d{8}T\d{12}Z_[0-9a-f]{32}", run_path.parent.name) is None:
            continue
        run = cast(ScanRun, json.loads(run_path.read_text(encoding="utf-8")))
        if run["run_id"] == run_path.parent.name:
            runs.append(run)
    runs.sort(key=lambda run: (run["started_at"], run["run_id"]), reverse=True)
    return runs
