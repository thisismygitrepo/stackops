import json
from pathlib import Path

from stackops.jobs.installer.checks.scan_history import ScanRun
from stackops.jobs.installer.checks.security_helper import render_csv_text

PROVENANCE_KEYS: tuple[str, ...] = (
    "run_id", "target_id", "app_name", "version", "app_path", "sha256", "checked_at", "analyzed_at", "source",
)
APP_EXPORT_KEYS: tuple[str, ...] = PROVENANCE_KEYS + (
    "status", "positive_pct", "flagged_engines", "verdict_engines", "total_engines", "app_url",
    "error_stage", "error_type", "error_code", "notes",
)
ENGINE_EXPORT_KEYS: tuple[str, ...] = PROVENANCE_KEYS + ("engine_name", "engine_category", "engine_result")
APP_TABLE_KEYS: tuple[str, ...] = (
    "target_id", "app_name", "version", "status", "checked_at", "analyzed_at", "source", "notes", "app_path",
)


def build_run_rows(run: ScanRun, app_names: set[str] | None) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    app_rows: list[dict[str, object]] = []
    engine_rows: list[dict[str, object]] = []
    for index, target in enumerate(run["targets"]):
        record = target["record"]
        app_name = record["app_data"]["app_name"] if record is not None else Path(target["path"]).stem
        if app_names is not None and app_name.lower() not in app_names:
            continue
        provenance: dict[str, object] = {
            "run_id": run["run_id"],
            "target_id": index + 1,
            "app_name": app_name,
            "version": target["version"],
            "app_path": target["path"],
            "sha256": target["sha256"],
            "checked_at": target["checked_at"],
            "analyzed_at": record["app_data"]["scan_time"] if record is not None else None,
            "source": target["source"],
        }
        error = target["error"]
        row: dict[str, object] = {
            **provenance,
            "status": "pending" if run["status"] == "running" else "not_scanned",
            "positive_pct": None,
            "flagged_engines": None,
            "verdict_engines": None,
            "total_engines": None,
            "app_url": "",
            "error_stage": error["stage"] if error else None,
            "error_type": error["error_type"] if error else None,
            "error_code": error["error_code"] if error else None,
            "notes": "No result recorded." if record is None else record["app_data"]["notes"],
        }
        if record is not None:
            data = record["app_data"]
            row.update(
                status="failed" if data["positive_pct"] is None else "success",
                positive_pct=data["positive_pct"], flagged_engines=data["flagged_engines"],
                verdict_engines=data["verdict_engines"], total_engines=data["total_engines"], app_url=data["app_url"],
            )
            for engine in record["engine_results"]:
                engine_rows.append({**provenance, **engine})
        app_rows.append(row)
    return app_rows, engine_rows


def export_run(run: ScanRun, output: Path) -> None:
    app_rows, engine_rows = build_run_rows(run, app_names=None)
    output.mkdir(parents=True, exist_ok=False)
    (output / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    (output / "apps.csv").write_text(render_csv_text(app_rows, APP_EXPORT_KEYS) + "\n", encoding="utf-8")
    (output / "engines.csv").write_text(render_csv_text(engine_rows, ENGINE_EXPORT_KEYS) + "\n", encoding="utf-8")
    (output / "accounts.csv").write_text(run["account_csv"], encoding="utf-8")
