import csv
import json
import os
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Literal, TypedDict

from stackops.jobs.installer.checks.run_reports import APP_EXPORT_KEYS, ENGINE_EXPORT_KEYS, build_run_rows, export_run
from stackops.jobs.installer.checks.scan_history import ScanRun
from stackops.jobs.installer.checks.scan_overview import RunSummary, summarize_run
from stackops.jobs.installer.checks.security_helper import render_csv_text
from stackops.scripts.python.helpers.helpers_webui.security_constants import EXPORT_FOLDER_PREFIX, EXPORT_HOME_FOLDER
from stackops.scripts.python.helpers.helpers_webui.security_scan_plans import ScanProblem, read_saved_run

# Whether an export can go to a typed folder. The command makes the folder and refuses one that is already there.
type ExportPlaceState = Literal["new", "exists", "blocked"]


# One file of an export. `rows` is how many lines of data a table holds, and None for the record that is not a table.
class ExportFile(TypedDict):
    name: str
    rows: int | None
    bytes: int


class ExportPlan(TypedDict):
    run: RunSummary
    files: list[ExportFile]
    suggested: str


class ExportPlace(TypedDict):
    path: str
    state: ExportPlaceState
    creates: int


class ExportOutcome(TypedDict):
    output: str
    files: list[ExportFile]


# The four files exactly as `export_run` writes them, so the sizes shown before the export are the sizes on disk after it.
def _export_files(run: ScanRun) -> list[ExportFile]:
    app_rows, engine_rows = build_run_rows(run, app_names=None)
    texts: list[tuple[str, int | None, str]] = [
        ("run.json", None, json.dumps(run, indent=2) + "\n"),
        ("apps.csv", len(app_rows), render_csv_text(app_rows, APP_EXPORT_KEYS) + "\n"),
        ("engines.csv", len(engine_rows), render_csv_text(engine_rows, ENGINE_EXPORT_KEYS) + "\n"),
        ("accounts.csv", sum(1 for _row in csv.DictReader(StringIO(run["account_csv"]))), run["account_csv"]),
    ]
    return [{"name": name, "rows": rows, "bytes": len(text.encode(encoding="utf-8"))} for name, rows, text in texts]


# A folder that is not there yet, named after when the scan started, in Downloads when this machine has one.
def _suggest_output(run: ScanRun) -> Path:
    downloads = Path.home() / EXPORT_HOME_FOLDER
    parent = downloads if downloads.is_dir() else Path.home()
    stem = f"""{EXPORT_FOLDER_PREFIX}-{datetime.fromisoformat(run["started_at"]).astimezone():%Y-%m-%d-%H%M}"""
    candidate = parent / stem
    number = 2
    while candidate.exists():
        candidate = parent / f"""{stem}-{number}"""
        number += 1
    return candidate


def read_export_plan(run_id: str) -> ExportPlan | ScanProblem:
    run = read_saved_run(run_id)
    match run:
        case ScanProblem():
            return run
        case _:
            return {"run": summarize_run(run), "files": _export_files(run), "suggested": str(_suggest_output(run))}


def check_export_place(output: Path) -> ExportPlace:
    if output.exists() or output.is_symlink():
        return {"path": str(output), "state": "exists", "creates": 0}
    # The folders above it that are missing are made too; the first one that exists has to be a folder this user can write in.
    creates = 1
    ancestor = output.parent
    while not ancestor.exists() and ancestor != ancestor.parent:
        creates += 1
        ancestor = ancestor.parent
    usable = ancestor.is_dir() and os.access(ancestor, os.W_OK | os.X_OK)
    return {"path": str(output), "state": "new" if usable else "blocked", "creates": creates}


def export_saved_run(run_id: str, output: Path) -> ExportOutcome | ScanProblem:
    run = read_saved_run(run_id)
    match run:
        case ScanProblem():
            return run
        case _:
            pass
    try:
        export_run(run, output)
    except FileExistsError:
        return ScanProblem(message="That folder already exists. An export needs a folder of its own.", status=409)
    except OSError as error:
        return ScanProblem(message=f"""The export could not be written. {error.strerror or error}""", status=400)
    return {"output": str(output), "files": [{"name": file["name"], "rows": file["rows"], "bytes": (output / file["name"]).stat().st_size} for file in _export_files(run)]}
