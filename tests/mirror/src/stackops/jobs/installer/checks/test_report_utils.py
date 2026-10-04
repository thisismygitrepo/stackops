from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from rich.console import Console

from stackops.jobs.installer.checks.check_installations import build_scan_record
from stackops.jobs.installer.checks.report_utils import AppData, app_safety_sort_key, build_app_metadata_row, build_latest_scan_panel, build_summary_group
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


def test_summary_orders_failed_unknown_and_riskiest_apps_first_without_mutating_input() -> None:
    results: list[ScanResult] = [{"engine_name": "sample-engine", "category": "undetected", "result": None}]
    template = build_scan_record(
        app_path=Path("sample"),
        version=None,
        app_url="",
        outcome=ScanSuccess(
            summary=summarize_scan_results(results),
            results=results,
            scanned_at=datetime(2026, 10, 4, 6, 44, tzinfo=UTC),
            source="existing_report",
        ),
    )["app_data"]
    cases: list[tuple[str, float | None, int, str]] = [
        ("clean-zeta", 0.0, 10, "z"),
        ("review-low", 1.0, 100, "a"),
        ("flagged-lower", 20.0, 100, "b"),
        ("failed-zeta", None, 0, "a"),
        ("flagged-zeta", 80.0, 100, "a"),
        ("no-verdicts", 0.0, 0, "a"),
        ("flagged-alpha", 80.0, 100, "z"),
        ("clean-alpha", 0.0, 10, "a"),
        ("failed-alpha", None, 0, "a"),
        ("flagged-alpha", 80.0, 100, "a"),
    ]
    data: list[AppData] = []
    for app_name, positive_pct, verdict_engines, app_path in cases:
        row = template.copy()
        row["app_name"] = app_name
        row["positive_pct"] = positive_pct
        row["verdict_engines"] = verdict_engines
        row["app_path"] = app_path
        data.append(row)
    original_data = [row.copy() for row in data]

    ordered = sorted(data, key=app_safety_sort_key)
    output = StringIO()
    Console(file=output, width=200).print(build_summary_group(data))

    expected_names = [
        "failed-alpha", "failed-zeta", "no-verdicts", "flagged-alpha", "flagged-alpha",
        "flagged-zeta", "flagged-lower", "review-low", "clean-alpha", "clean-zeta",
    ]
    assert [row["app_name"] for row in ordered] == expected_names
    assert [row["app_path"] for row in ordered[3:5]] == ["a", "z"]
    displayed = output.getvalue()
    unique_names = list(dict.fromkeys(expected_names))
    assert [displayed.index(name) for name in unique_names] == sorted(displayed.index(name) for name in unique_names)
    assert data == original_data
