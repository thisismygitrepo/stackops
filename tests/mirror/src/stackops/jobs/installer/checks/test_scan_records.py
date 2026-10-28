from datetime import UTC, datetime
from pathlib import Path

import pytest

from stackops.jobs.installer.checks.report_utils import ScannedAppRecord
from stackops.jobs.installer.checks.scan_history import create_run, load_run, save_run
from stackops.jobs.installer.checks.scan_outcomes import ScanFailure, ScanSource, ScanSuccess, format_scan_failure
from stackops.jobs.installer.checks.scan_records import build_scan_record
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results

DUMMY_SHA256 = "a" * 64


def _reload(root: Path, record: ScannedAppRecord) -> ScannedAppRecord:
    run = create_run(root, "path", ["rg"], [(Path("rg"), "1")], None)
    run["targets"][0]["record"] = record
    save_run(root, run)
    reloaded = load_run(root, run["run_id"])["targets"][0]["record"]
    assert reloaded is not None
    return reloaded


def test_failed_scan_record_has_no_summary_and_keeps_error_note_when_reloaded(tmp_path: Path) -> None:
    outcome = ScanFailure(stage="analysis polling", error_type="APIError", error_code="QuotaExceededError", sha256=DUMMY_SHA256)
    record = build_scan_record(app_path=Path("rg"), version="1", app_url="", outcome=outcome)

    reloaded = _reload(tmp_path / "records", record)

    assert reloaded == record
    assert reloaded["app_data"]["positive_pct"] is None
    assert reloaded["app_data"]["scan_time"] == ""
    assert reloaded["app_data"]["notes"] == format_scan_failure(outcome)
    assert reloaded["engine_results"] == []


@pytest.mark.parametrize(("source", "note_prefix"), [("existing_report", "Existing VirusTotal report. "), ("submitted_file", "")])
def test_scan_record_preserves_source_and_scan_date_when_reloaded(source: ScanSource, note_prefix: str, tmp_path: Path) -> None:
    results: list[ScanResult] = [{"engine_name": "sample-engine", "category": "undetected", "result": None}]
    summary = summarize_scan_results(results)
    scanned_at = datetime(2026, 10, 3, 1, 2, tzinfo=UTC)
    record = build_scan_record(
        app_path=Path("rg"),
        version="1",
        app_url="https://example.invalid/rg",
        outcome=ScanSuccess(summary=summary, results=results, scanned_at=scanned_at, source=source, sha256=DUMMY_SHA256),
    )

    reloaded = _reload(tmp_path / "records", record)

    assert reloaded == record
    assert reloaded["app_data"]["positive_pct"] == 0.0
    assert reloaded["app_data"]["scan_time"] == scanned_at.isoformat()
    assert reloaded["app_data"]["notes"] == note_prefix + summary["notes"]
    assert [row["engine_name"] for row in reloaded["engine_results"]] == ["sample-engine"]
