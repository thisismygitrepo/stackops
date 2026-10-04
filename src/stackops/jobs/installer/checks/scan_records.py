from datetime import UTC
from pathlib import Path
from typing import assert_never

import stackops.utils.path_core as path_core
from stackops.jobs.installer.checks.report_utils import AppData, ScannedAppRecord, build_engine_report_rows
from stackops.jobs.installer.checks.scan_outcomes import ScanFailure, ScanSuccess, format_scan_failure


def build_scan_record(
    app_path: Path,
    version: str | None,
    app_url: str,
    outcome: ScanSuccess | ScanFailure,
) -> ScannedAppRecord:
    app_data: AppData = {
        "app_name": app_path.stem,
        "version": version,
        "positive_pct": None,
        "flagged_engines": 0,
        "verdict_engines": 0,
        "total_engines": 0,
        "malicious_engines": 0,
        "suspicious_engines": 0,
        "harmless_engines": 0,
        "undetected_engines": 0,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": "",
        "scan_time": "",
        "app_path": path_core.collapseuser(app_path, strict=False).as_posix(),
        "app_url": app_url,
    }
    match outcome:
        case ScanSuccess():
            scan_summary = outcome.summary
            app_data["positive_pct"] = scan_summary["positive_pct"]
            app_data["flagged_engines"] = scan_summary["flagged_engines"]
            app_data["verdict_engines"] = scan_summary["verdict_engines"]
            app_data["total_engines"] = scan_summary["total_engines"]
            app_data["malicious_engines"] = scan_summary["malicious_engines"]
            app_data["suspicious_engines"] = scan_summary["suspicious_engines"]
            app_data["harmless_engines"] = scan_summary["harmless_engines"]
            app_data["undetected_engines"] = scan_summary["undetected_engines"]
            app_data["unsupported_engines"] = scan_summary["unsupported_engines"]
            app_data["timeout_engines"] = scan_summary["timeout_engines"]
            app_data["failure_engines"] = scan_summary["failure_engines"]
            app_data["other_engines"] = scan_summary["other_engines"]
            match outcome.source:
                case "existing_report":
                    source_note = "Existing VirusTotal report. "
                case "submitted_file":
                    source_note = ""
                case _:
                    assert_never(outcome.source)
            app_data["notes"] = source_note + scan_summary["notes"]
            app_data["scan_time"] = outcome.scanned_at.astimezone(UTC).isoformat()
            engine_results = build_engine_report_rows(app_data, outcome.results)
        case ScanFailure():
            app_data["notes"] = format_scan_failure(outcome)
            engine_results = []
        case _:
            assert_never(outcome)
    return {"app_data": app_data, "engine_results": engine_results}
