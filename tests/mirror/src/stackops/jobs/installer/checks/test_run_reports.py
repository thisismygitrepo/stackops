from pathlib import Path

from stackops.jobs.installer.checks.run_reports import build_run_rows
from stackops.jobs.installer.checks.scan_history import create_run, load_run, save_run
from stackops.jobs.installer.checks.scan_outcomes import ScanFailure
from stackops.jobs.installer.checks.scan_records import build_scan_record

DUMMY_SHA256 = "a" * 64


def test_stored_failed_scan_is_reported_as_failed_with_error_details(tmp_path: Path) -> None:
    outcome = ScanFailure(stage="analysis polling", error_type="APIError", error_code="QuotaExceededError", sha256=DUMMY_SHA256)
    record = build_scan_record(app_path=Path("rg"), version="1", app_url="", outcome=outcome)
    run = create_run(tmp_path, "path", ["rg"], [(Path("rg"), "1")], None)
    target = run["targets"][0]
    target["record"] = record
    target["sha256"] = DUMMY_SHA256
    target["checked_at"] = "2026-10-05T00:00:00+00:00"
    target["error"] = {"stage": outcome.stage, "error_type": outcome.error_type, "error_code": outcome.error_code}
    run["status"] = "completed_with_errors"
    save_run(tmp_path, run)

    app_rows, engine_rows = build_run_rows(load_run(tmp_path, run["run_id"]), app_names=None)

    assert engine_rows == []
    assert len(app_rows) == 1
    row = app_rows[0]
    assert row["status"] == "failed"
    assert row["positive_pct"] is None
    assert (row["error_stage"], row["error_type"], row["error_code"]) == ("analysis polling", "APIError", "QuotaExceededError")
    assert row["sha256"] == DUMMY_SHA256
    assert row["notes"] == record["app_data"]["notes"]
