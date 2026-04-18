# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path

import pytest
import rich.console as rich_console
import typer

from stackops.jobs.installer.checks import check_installations, install_utils, security_helper, vt_utils


class RecordingConsole:
    instances: list[RecordingConsole] = []

    def __init__(self) -> None:
        self.messages: list[object] = []
        self.__class__.instances.append(self)

    def print(self, message: object) -> None:
        self.messages.append(message)


class FakeClientContext:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, traceback: object | None) -> None:
        return None


def test_parse_helpers_normalize_runtime_values() -> None:
    assert security_helper._parse_positive_pct(None) is None
    assert security_helper._parse_positive_pct(" None ") is None
    assert security_helper._parse_positive_pct("4.5") == 4.5
    assert security_helper._parse_positive_pct("bogus") is None
    assert security_helper._parse_bool(True) is True
    assert security_helper._parse_bool(" YES ") is True
    assert security_helper._parse_bool("no") is False
    assert security_helper.normalize_app_names([" Alpha ", "", "BETA"]) == {"alpha", "beta"}
    assert security_helper.parse_apps_argument(" alpha, beta , ,gamma ") == ["alpha", "beta", "gamma"]
    assert security_helper.parse_apps_argument("") is None


def test_to_metadata_and_engine_rows_normalize_optional_fields() -> None:
    app_rows = security_helper.to_app_metadata_list(
        [
            {
                "app_name": "alpha",
                "version": "",
                "scan_time": "2026-04-12 12:00",
                "app_path": "/tmp/alpha",
                "app_url": "",
                "positive_pct": "0.0",
                "notes": "clean",
            }
        ]
    )
    engine_rows = security_helper.to_engine_report_rows(
        [{"app_name": "alpha", "engine_name": "EngineA", "engine_category": "harmless", "engine_result": ""}]
    )

    assert app_rows == [
        {
            "app_name": "alpha",
            "version": None,
            "scan_time": "2026-04-12 12:00",
            "app_path": "/tmp/alpha",
            "app_url": "",
            "scan_summary_available": True,
            "notes": "clean",
        }
    ]
    assert engine_rows == [{"app_name": "alpha", "engine_name": "EngineA", "engine_category": "harmless", "engine_result": None}]


def test_build_app_data_list_and_hydrate_engine_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    app_rows: list[security_helper.AppMetadataRow] = [
        {
            "app_name": "alpha",
            "version": "1.0.0",
            "scan_time": "2026-04-12 12:30",
            "app_path": "/tmp/alpha",
            "app_url": "https://example.test/alpha",
            "scan_summary_available": True,
            "notes": "original",
        },
        {
            "app_name": "beta",
            "version": None,
            "scan_time": "2026-04-12 12:31",
            "app_path": "/tmp/beta",
            "app_url": "",
            "scan_summary_available": False,
            "notes": "pending",
        },
    ]
    engine_rows: list[security_helper.StoredEngineReportRow] = [
        {"app_name": "alpha", "engine_name": "EngineA", "engine_category": "harmless", "engine_result": "ok"},
        {"app_name": "missing", "engine_name": "EngineB", "engine_category": "failure", "engine_result": "timeout"},
    ]

    monkeypatch.setattr(
        security_helper,
        "summarize_scan_results",
        lambda rows: {
            "positive_pct": 0.0,
            "flagged_engines": 0,
            "verdict_engines": 1,
            "total_engines": 1,
            "malicious_engines": 0,
            "suspicious_engines": 0,
            "harmless_engines": 1,
            "undetected_engines": 0,
            "unsupported_engines": 0,
            "timeout_engines": 0,
            "failure_engines": 0,
            "other_engines": 0,
            "notes": "derived",
        },
    )

    app_data_list = security_helper.build_app_data_list(app_rows, engine_rows)
    hydrated_engine_rows = security_helper.hydrate_engine_report_rows(app_rows, engine_rows)

    assert app_data_list[0]["positive_pct"] == 0.0
    assert app_data_list[0]["notes"] == "derived"
    assert app_data_list[1]["positive_pct"] is None
    assert hydrated_engine_rows[0]["version"] == "1.0.0"
    assert hydrated_engine_rows[1]["version"] is None
    assert hydrated_engine_rows[1]["app_path"] == ""


def test_render_csv_text_and_build_report_stats_lines() -> None:
    csv_text = security_helper.render_csv_text([{"app_name": "alpha", "engine_result": None}], ["app_name", "engine_result"])
    stats_lines = security_helper.build_report_stats_lines(
        [
            {
                "app_name": "clean",
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
                "notes": "",
                "scan_time": "2026-04-12 13:00",
                "app_path": "/tmp/clean",
                "app_url": "",
            },
            {
                "app_name": "flagged",
                "version": "2.0.0",
                "positive_pct": 10.0,
                "flagged_engines": 1,
                "verdict_engines": 2,
                "total_engines": 3,
                "malicious_engines": 1,
                "suspicious_engines": 0,
                "harmless_engines": 1,
                "undetected_engines": 1,
                "unsupported_engines": 0,
                "timeout_engines": 0,
                "failure_engines": 0,
                "other_engines": 0,
                "notes": "",
                "scan_time": "2026-04-12 13:01",
                "app_path": "/tmp/flagged",
                "app_url": "",
            },
            {
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
                "scan_time": "2026-04-12 13:02",
                "app_path": "/tmp/pending",
                "app_url": "",
            },
        ],
        Path("/tmp/apps.csv"),
        Path("/tmp/engines.csv"),
    )

    assert csv_text.splitlines() == ["app_name,engine_result", "alpha,"]
    assert stats_lines == [
        "Apps in report: 3",
        "Scanned: 2",
        "Clean: 1",
        "Review (<5%): 0",
        "Flagged (>=5%): 1",
        "No verdicts: 0",
        "Engines: 5",
        "Verdict engines: 4",
        "Flagged engines: 1",
        "App metadata CSV: /tmp/apps.csv",
        "Engine CSV: /tmp/engines.csv",
    ]


def test_load_filtered_report_rows_filters_and_hydrates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        install_utils,
        "load_app_metadata_report",
        lambda: [
            {
                "app_name": "alpha",
                "version": "1.0.0",
                "scan_time": "2026-04-12 13:30",
                "app_path": "/tmp/alpha",
                "app_url": "",
                "scan_summary_available": "true",
                "notes": "",
            },
            {
                "app_name": "beta",
                "version": "2.0.0",
                "scan_time": "2026-04-12 13:31",
                "app_path": "/tmp/beta",
                "app_url": "",
                "scan_summary_available": "false",
                "notes": "",
            },
        ],
    )
    monkeypatch.setattr(
        install_utils,
        "load_engine_results_report",
        lambda: [
            {"app_name": "alpha", "engine_name": "EngineA", "engine_category": "harmless", "engine_result": "ok"},
            {"app_name": "beta", "engine_name": "EngineB", "engine_category": "failure", "engine_result": "timeout"},
        ],
    )
    monkeypatch.setattr(
        security_helper,
        "summarize_scan_results",
        lambda rows: {
            "positive_pct": 0.0,
            "flagged_engines": 0,
            "verdict_engines": 1,
            "total_engines": 1,
            "malicious_engines": 0,
            "suspicious_engines": 0,
            "harmless_engines": 1,
            "undetected_engines": 0,
            "unsupported_engines": 0,
            "timeout_engines": 0,
            "failure_engines": 0,
            "other_engines": 0,
            "notes": "derived",
        },
    )

    app_rows, engine_rows, app_data_list, hydrated_engine_rows = security_helper.load_filtered_report_rows({"alpha"})

    assert [row["app_name"] for row in app_rows] == ["alpha"]
    assert [row["app_name"] for row in engine_rows] == ["alpha"]
    assert app_data_list[0]["notes"] == "derived"
    assert hydrated_engine_rows[0]["version"] == "1.0.0"


def test_scan_single_path_exits_when_credentials_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    RecordingConsole.instances.clear()
    monkeypatch.setattr(rich_console, "Console", RecordingConsole)

    def fail_get_vt_client() -> object:
        raise FileNotFoundError("missing VT credentials")

    monkeypatch.setattr(vt_utils, "get_vt_client", fail_get_vt_client)

    with pytest.raises(typer.Exit) as exit_info:
        security_helper.scan_single_path(Path("/tmp/tool"), True)

    assert exit_info.value.exit_code == 1
    assert any("missing VT credentials" in str(message) for message in RecordingConsole.instances[-1].messages)


def test_scan_single_path_without_recording_prints_summary_only(monkeypatch: pytest.MonkeyPatch) -> None:
    RecordingConsole.instances.clear()
    monkeypatch.setattr(rich_console, "Console", RecordingConsole)
    monkeypatch.setattr(vt_utils, "get_vt_client", lambda: FakeClientContext())
    monkeypatch.setattr(
        vt_utils,
        "scan_file",
        lambda path, client: (
            {
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
                "notes": "clean",
            },
            [],
        ),
    )

    def fail_write_reports(scan_records: list[object]) -> tuple[Path, Path]:
        raise AssertionError(f"write_reports should not run: {scan_records!r}")

    monkeypatch.setattr(check_installations, "write_reports", fail_write_reports)

    security_helper.scan_single_path(Path("/tmp/tool"), False)

    messages = RecordingConsole.instances[-1].messages
    assert any("tool: 0/2 flagged (0.0%)" in str(message) for message in messages)
    assert "Notes: clean" in messages
    assert "[yellow]Scan results were not saved to the repo reports.[/yellow]" in messages


def test_scan_single_path_records_report_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    RecordingConsole.instances.clear()
    monkeypatch.setattr(rich_console, "Console", RecordingConsole)
    monkeypatch.setattr(vt_utils, "get_vt_client", lambda: FakeClientContext())
    monkeypatch.setattr(
        vt_utils,
        "scan_file",
        lambda path, client: (
            {
                "positive_pct": 0.0,
                "flagged_engines": 0,
                "verdict_engines": 1,
                "total_engines": 1,
                "malicious_engines": 0,
                "suspicious_engines": 0,
                "harmless_engines": 1,
                "undetected_engines": 0,
                "unsupported_engines": 0,
                "timeout_engines": 0,
                "failure_engines": 0,
                "other_engines": 0,
                "notes": "stored",
            },
            [{"engine_name": "EngineA", "category": "harmless", "result": "ok"}],
        ),
    )
    monkeypatch.setattr(check_installations, "build_scan_record", lambda **kwargs: {"record": "ok", "kwargs": kwargs})
    monkeypatch.setattr(check_installations, "write_reports", lambda scan_records: (Path("/tmp/apps.csv"), Path("/tmp/engines.csv")))

    security_helper.scan_single_path(Path("/tmp/tool"), True)

    messages = RecordingConsole.instances[-1].messages
    assert "[green]App metadata CSV report saved to: /tmp/apps.csv[/green]" in messages
    assert "[green]Engine CSV report saved to: /tmp/engines.csv[/green]" in messages
