from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from rich.console import Console

from stackops.jobs.installer.checks.check_installations import build_scan_record
from stackops.jobs.installer.checks.report_utils import build_app_metadata_row, build_latest_scan_panel, build_summary_group
from stackops.jobs.installer.checks.scan_outcomes import ScanFailure, ScanSuccess
from stackops.jobs.installer.checks.security_helper import build_app_data_list, build_report_stats_lines
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results


def test_stored_failed_scan_displays_failed_status_and_error() -> None:
    record = build_scan_record(
        app_path=Path("rg"),
        version="1",
        app_url="",
        outcome=ScanFailure(stage="analysis polling", error_type="APIError", error_code="QuotaExceededError"),
    )
    metadata = build_app_metadata_row(record["app_data"])
    reloaded = build_app_data_list([metadata], record["engine_results"])
    output = StringIO()
    console = Console(file=output, width=200)

    console.print(build_latest_scan_panel(reloaded[0], completed_count=1, total_count=1))
    console.print(build_summary_group(reloaded))

    assert metadata["scan_summary_available"] is False
    assert record["engine_results"] == []
    assert reloaded[0]["notes"] == record["app_data"]["notes"]
    displayed = output.getvalue()
    assert "Failed" in displayed
    assert "failed 1" in displayed
    assert "1/1 processed" in displayed
    assert "QuotaExceededError" in displayed
    assert "analysis polling" in displayed
    assert "Attempted" in displayed
    assert "Pending" not in displayed
    assert "complete" not in displayed
    stats_lines = build_report_stats_lines(reloaded, app_metadata_path=Path("metadata.csv"), engine_results_path=Path("engines.csv"))
    assert "Scanned: 0" in stats_lines
    assert "Failed: 1" in stats_lines


def test_existing_report_preserves_source_and_scan_date_when_reloaded() -> None:
    results: list[ScanResult] = [{"engine_name": "sample-engine", "category": "undetected", "result": None}]
    scanned_at = datetime(2026, 10, 3, 1, 2, tzinfo=UTC)
    record = build_scan_record(
        app_path=Path("rg"),
        version="1",
        app_url="https://example.invalid/rg",
        outcome=ScanSuccess(summary=summarize_scan_results(results), results=results, scanned_at=scanned_at, source="existing_report"),
    )
    metadata = build_app_metadata_row(record["app_data"])

    reloaded = build_app_data_list([metadata], record["engine_results"])

    assert metadata["scan_summary_available"] is True
    assert reloaded[0] == record["app_data"]
    assert reloaded[0]["scan_time"] == scanned_at.astimezone().strftime("%Y-%m-%d %H:%M")
    assert reloaded[0]["notes"].startswith("Existing VirusTotal report. ")


def test_engine_unsupported_results_display_no_verdicts_instead_of_failed() -> None:
    results: list[ScanResult] = [{"engine_name": "sample-engine", "category": "type-unsupported", "result": None}]
    record = build_scan_record(
        app_path=Path("rg"),
        version=None,
        app_url="",
        outcome=ScanSuccess(
            summary=summarize_scan_results(results),
            results=results,
            scanned_at=datetime(2026, 10, 4, 6, 44, tzinfo=UTC),
            source="submitted_file",
        ),
    )
    output = StringIO()

    Console(file=output, width=200).print(build_summary_group([record["app_data"]]))

    displayed = output.getvalue()
    assert "No verdicts (1 engines)" in displayed
    assert "failed 0" in displayed
    assert "Failed" not in displayed
