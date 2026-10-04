from typing import cast

import pytest
import vt

from stackops.jobs.installer.checks.scan_outcomes import ScanFailure, format_scan_failure
from stackops.jobs.installer.checks.vt_utils import normalize_scan_results, summarize_scan_results


def test_sdk_engine_results_use_only_verdicts_for_detection_percentage() -> None:
    report = vt.Object(
        "file",
        "sample",
        {
            "last_analysis_results": {
                "A": {"category": "malicious", "result": "Detected"},
                "B": {"category": "undetected", "result": None},
                "C": {"category": "type-unsupported", "result": None},
                "D": {"category": "timeout", "result": None},
            }
        },
    )
    results = normalize_scan_results(cast(object, report.last_analysis_results))
    summary = summarize_scan_results(results)

    assert summary["total_engines"] == 4
    assert summary["verdict_engines"] == 2
    assert summary["flagged_engines"] == 1
    assert summary["positive_pct"] == 50.0
    assert summary["unsupported_engines"] == 1
    assert summary["timeout_engines"] == 1


@pytest.mark.parametrize(
    "raw_results",
    [None, [], "broken", {"A": []}, {7: {"category": "undetected"}}, {"A": {"result": None}}, {"A": {"category": 4}}, {"A": {"category": "undetected", "result": 9}}],
)
def test_malformed_results_are_not_treated_as_empty_reports(raw_results: object) -> None:
    with pytest.raises(ValueError):
        normalize_scan_results(raw_results)


def test_completed_empty_results_have_no_verdict() -> None:
    summary = summarize_scan_results(normalize_scan_results({}))

    assert summary["total_engines"] == 0
    assert summary["verdict_engines"] == 0
    assert summary["notes"] == "VirusTotal returned no engine results."


def test_failure_format_keeps_only_stage_type_and_safe_api_code() -> None:
    failure = ScanFailure(stage="report lookup", error_type="APIError", error_code="WrongCredentialsError")
    unsafe = ScanFailure(stage="file upload", error_type="[unsafe]", error_code="failure\nsecret=value")

    assert format_scan_failure(failure) == "VirusTotal report lookup failed: APIError (WrongCredentialsError)."
    assert format_scan_failure(unsafe) == "VirusTotal file upload failed: UnknownError (InvalidErrorCode)."
