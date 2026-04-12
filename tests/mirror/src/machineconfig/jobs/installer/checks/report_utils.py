from __future__ import annotations

from machineconfig.jobs.installer.checks import report_utils


def test_build_app_metadata_row_and_engine_rows() -> None:
    app_data: report_utils.AppData = {
        "app_name": "alpha",
        "version": "1.0.0",
        "positive_pct": 0.0,
        "flagged_engines": 0,
        "verdict_engines": 2,
        "total_engines": 4,
        "malicious_engines": 0,
        "suspicious_engines": 0,
        "harmless_engines": 2,
        "undetected_engines": 2,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": "clean",
        "scan_time": "2026-04-12 11:00",
        "app_path": "/tmp/alpha",
        "app_url": "https://example.test/alpha",
    }

    assert report_utils.build_app_metadata_row(app_data) == {
        "app_name": "alpha",
        "version": "1.0.0",
        "scan_time": "2026-04-12 11:00",
        "app_path": "/tmp/alpha",
        "app_url": "https://example.test/alpha",
        "scan_summary_available": True,
        "notes": "clean",
    }
    assert report_utils.build_engine_report_rows(app_data, [{"engine_name": "EngineA", "category": "harmless", "result": "ok"}]) == [
        {
            "app_name": "alpha",
            "engine_name": "EngineA",
            "engine_category": "harmless",
            "engine_result": "ok",
        }
    ]


def test_status_and_safety_labels_cover_runtime_thresholds() -> None:
    pending_row: report_utils.AppData = {
        "app_name": "pending",
        "version": None,
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
        "scan_time": "2026-04-12 11:00",
        "app_path": "/tmp/pending",
        "app_url": "",
    }
    clean_row = pending_row | {
        "app_name": "clean",
        "positive_pct": 0.0,
        "verdict_engines": 4,
        "total_engines": 4,
        "harmless_engines": 4,
        "notes": "All reporting engines returned a verdict.",
    }
    review_row = clean_row | {"app_name": "review", "positive_pct": 4.0, "flagged_engines": 1, "suspicious_engines": 1}
    flagged_row = clean_row | {"app_name": "flagged", "positive_pct": 5.0, "flagged_engines": 2, "malicious_engines": 2}
    no_verdict_row = pending_row | {"app_name": "no-verdict", "positive_pct": 0.0, "total_engines": 5}

    assert report_utils._get_row_status(pending_row) == "pending"
    assert report_utils._get_row_status(no_verdict_row) == "no_verdict"
    assert report_utils._get_row_status(clean_row) == "clean"
    assert report_utils._get_row_status(review_row) == "review"
    assert report_utils._get_row_status(flagged_row) == "flagged"
    assert report_utils._build_safety_label(clean_row) == "Clean 0/4 (0.0%)"
    assert report_utils._build_safety_label(review_row) == "Review 1/4 (4.0%)"
    assert report_utils._build_safety_label(flagged_row) == "Flagged 2/4 (5.0%)"
    assert report_utils._build_safety_label(no_verdict_row) == "No verdicts (5 engines)"


def test_build_latest_scan_panel_and_engine_results_table() -> None:
    app_data: report_utils.AppData = {
        "app_name": "alpha",
        "version": "1.0.0",
        "positive_pct": 0.0,
        "flagged_engines": 0,
        "verdict_engines": 2,
        "total_engines": 2,
        "malicious_engines": 0,
        "suspicious_engines": 0,
        "harmless_engines": 2,
        "undetected_engines": 0,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": "All reporting engines returned a verdict.",
        "scan_time": "2026-04-12 11:30",
        "app_path": "/tmp/alpha",
        "app_url": "https://example.test/alpha",
    }
    waiting_panel = report_utils.build_latest_scan_panel(None, 0, 2)
    latest_panel = report_utils.build_latest_scan_panel(app_data, 1, 2)
    summary_group = report_utils.build_summary_group([app_data])
    engine_table = report_utils.build_engine_results_table(
        [
            {
                "app_name": "alpha",
                "version": "1.0.0",
                "scan_time": "2026-04-12 11:30",
                "app_path": "/tmp/alpha",
                "app_url": "https://example.test/alpha",
                "engine_name": "EngineA",
                "engine_category": "harmless",
                "engine_result": "ok",
            }
        ]
    )

    assert waiting_panel.subtitle == "0/2 complete"
    assert waiting_panel.renderable.plain.startswith("Waiting for the first completed scan")
    assert latest_panel.title == "Latest Scan Result"
    assert latest_panel.subtitle == "1/2 complete"
    assert len(summary_group.renderables) == 2
    assert [column.header for column in engine_table.columns] == ["App", "Ver", "Engine", "Category", "Result", "Scanned", "Path"]
    assert len(engine_table.rows) == 1
