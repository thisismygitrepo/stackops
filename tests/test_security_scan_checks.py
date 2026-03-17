import csv
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

from machineconfig.jobs.installer.checks import check_installations, security_cli, vt_utils
from machineconfig.jobs.installer.checks.report_utils import ScannedAppRecord
from machineconfig.utils.path_extended import PathExtended
from typer.testing import CliRunner

if TYPE_CHECKING:
    import vt


class FakeConsole:
    def __init__(self) -> None:
        self.renderables: list[object] = []

    def print(self, renderable: object) -> None:
        self.renderables.append(renderable)


def _build_sample_report_rows() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    app_rows: list[dict[str, object]] = [
        {
            "app_name": "zellij",
            "version": "v0.43.1",
            "scan_time": "2026-03-17 06:05",
            "app_path": "~/.local/bin/zellij",
            "app_url": "https://example.test/zellij",
            "scan_summary_available": "True",
            "notes": "All reporting engines returned a verdict.",
        }
    ]
    engine_rows: list[dict[str, object]] = [
        {"app_name": "zellij", "engine_name": "engine-a", "engine_category": "harmless", "engine_result": "clean"},
        {"app_name": "zellij", "engine_name": "engine-b", "engine_category": "undetected", "engine_result": None},
    ]
    return app_rows, engine_rows


def test_summarize_scan_results_uses_only_flagging_categories_for_positive_pct() -> None:
    results: list[vt_utils.ScanResult] = [
        {"engine_name": "engine-a", "category": "undetected", "result": None},
        {"engine_name": "engine-b", "category": "harmless", "result": "clean"},
        {"engine_name": "engine-c", "category": "suspicious", "result": "heuristic match"},
        {"engine_name": "engine-d", "category": "timeout", "result": None},
        {"engine_name": "engine-e", "category": "type-unsupported", "result": None},
    ]

    summary = vt_utils.summarize_scan_results(results)

    assert summary["flagged_engines"] == 1
    assert summary["verdict_engines"] == 3
    assert summary["total_engines"] == 5
    assert summary["positive_pct"] == 33.3
    assert summary["notes"] == "Excluded from percentage: 1 timed out, 1 unsupported"


def test_scan_file_supports_mapping_results(tmp_path: Path) -> None:
    class FakeAnalysis:
        id = "analysis-1"

    class FakeAnalysisResult:
        status = "completed"
        results = {
            "engine-a": {"category": "undetected", "result": None},
            "engine-b": {"category": "suspicious", "result": "heuristic"},
        }

    class FakeClient:
        def scan_file(self, _file_handle: object) -> FakeAnalysis:
            return FakeAnalysis()

        def get_object(self, _path: str, _analysis_id: str) -> FakeAnalysisResult:
            return FakeAnalysisResult()

    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"test")

    summary, results = vt_utils.scan_file(sample_path, cast("vt.Client", FakeClient()))

    assert summary is not None
    assert results == [
        {"engine_name": "engine-a", "category": "undetected", "result": None},
        {"engine_name": "engine-b", "category": "suspicious", "result": "heuristic"},
    ]
    assert summary["flagged_engines"] == 1
    assert summary["verdict_engines"] == 2
    assert summary["other_engines"] == 0


def test_scan_apps_with_vt_closes_vt_client_session() -> None:
    class FakeLive:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.renderable: object | None = None

        def __enter__(self) -> "FakeLive":
            return self

        def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
            return None

        def update(self, renderable: object) -> None:
            self.renderable = renderable

    class FakeClientContext:
        def __init__(self) -> None:
            self.closed = False
            self.client = object()

        def __enter__(self) -> object:
            return self.client

        def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
            self.closed = True
            return None

    fake_client = FakeClientContext()
    scan_summary: vt_utils.ScanSummary = {
        "positive_pct": 1.4,
        "total_engines": 72,
        "verdict_engines": 72,
        "flagged_engines": 1,
        "malicious_engines": 0,
        "suspicious_engines": 1,
        "harmless_engines": 0,
        "undetected_engines": 71,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": "All reporting engines returned a verdict.",
    }

    with (
        patch.object(check_installations, "Live", FakeLive),
        patch.object(check_installations, "get_vt_client", return_value=fake_client),
        patch.object(check_installations, "scan_file", return_value=(scan_summary, [])),
        patch.object(check_installations, "upload_app", return_value="https://example.test/zellij"),
    ):
        scan_records = check_installations.scan_apps_with_vt([(PathExtended("/tmp/zellij"), "v0.43.1")])

    assert fake_client.closed is True
    assert len(scan_records) == 1
    assert scan_records[0]["app_data"]["positive_pct"] == 1.4
    assert scan_records[0]["app_data"]["flagged_engines"] == 1
    assert scan_records[0]["app_data"]["verdict_engines"] == 72
    assert scan_records[0]["app_data"]["notes"] == "All reporting engines returned a verdict."
    assert scan_records[0]["engine_results"] == []


def test_build_app_data_list_derives_summary_from_joined_rows() -> None:
    app_rows: list[dict[str, object]] = [
        {
            "app_name": "zellij",
            "version": "v0.43.1",
            "scan_time": "2026-03-17 06:05",
            "app_path": "~/.local/bin/zellij",
            "app_url": "https://example.test/zellij",
            "scan_summary_available": "true",
            "notes": "",
        }
    ]
    engine_rows: list[dict[str, object]] = [
        {"app_name": "zellij", "engine_name": "engine-a", "engine_category": "harmless", "engine_result": "clean"},
        {"app_name": "zellij", "engine_name": "engine-b", "engine_category": "undetected", "engine_result": None},
    ]

    app_data_list = security_cli.build_app_data_list(
        security_cli.to_app_metadata_list(app_rows),
        security_cli.to_engine_report_rows(engine_rows),
    )

    assert len(app_data_list) == 1
    assert app_data_list[0]["flagged_engines"] == 0
    assert app_data_list[0]["verdict_engines"] == 2
    assert app_data_list[0]["total_engines"] == 2
    assert app_data_list[0]["notes"] == "All reporting engines returned a verdict."


def test_build_app_data_list_preserves_pending_rows() -> None:
    app_data_list = security_cli.build_app_data_list(
        security_cli.to_app_metadata_list(
            [
                {
                    "app_name": "zellij",
                    "version": "v0.43.1",
                    "scan_time": "2026-03-17 06:05",
                    "app_path": "~/.local/bin/zellij",
                    "app_url": "https://example.test/zellij",
                    "scan_summary_available": "false",
                    "notes": "VirusTotal credentials missing.",
                }
            ]
        ),
        [],
    )

    assert len(app_data_list) == 1
    assert app_data_list[0]["positive_pct"] is None
    assert app_data_list[0]["notes"] == "VirusTotal credentials missing."


def test_write_reports_creates_app_metadata_and_engine_csv(tmp_path: Path) -> None:
    app_metadata_path = tmp_path / "apps_metadata_report.csv"
    engine_path = tmp_path / "apps_engine_results_report.csv"
    scan_records: list[ScannedAppRecord] = [
        {
            "app_data": {
                "app_name": "zellij",
                "version": "v0.43.1",
                "positive_pct": 0.0,
                "flagged_engines": 0,
                "verdict_engines": 2,
                "total_engines": 2,
                "malicious_engines": 0,
                "suspicious_engines": 0,
                "harmless_engines": 1,
                "undetected_engines": 1,
                "unsupported_engines": 0,
                "timeout_engines": 0,
                "failure_engines": 0,
                "other_engines": 0,
                "notes": "All reporting engines returned a verdict.",
                "scan_time": "2026-03-17 07:35",
                "app_path": "~/.local/bin/zellij",
                "app_url": "https://example.test/zellij",
            },
            "engine_results": [
                {
                    "app_name": "zellij",
                    "engine_name": "engine-a",
                    "engine_category": "harmless",
                    "engine_result": "clean",
                },
                {
                    "app_name": "zellij",
                    "engine_name": "engine-b",
                    "engine_category": "undetected",
                    "engine_result": None,
                },
            ],
        }
    ]

    with (
        patch.object(check_installations, "APP_METADATA_PATH", app_metadata_path),
        patch.object(check_installations, "ENGINE_RESULTS_PATH", engine_path),
    ):
        written_app_metadata_path, written_engine_path = check_installations.write_reports(scan_records)

    assert written_app_metadata_path == app_metadata_path
    assert written_engine_path == engine_path
    assert app_metadata_path.exists()
    assert engine_path.exists()

    with app_metadata_path.open("r", encoding="utf-8") as file_handle:
        app_rows = list(csv.DictReader(file_handle))
    with engine_path.open("r", encoding="utf-8") as file_handle:
        engine_rows = list(csv.DictReader(file_handle))

    assert len(app_rows) == 1
    assert app_rows[0]["app_name"] == "zellij"
    assert app_rows[0]["scan_summary_available"] == "True"
    assert len(engine_rows) == 2
    assert engine_rows[0]["engine_name"] == "engine-a"
    assert engine_rows[1]["engine_category"] == "undetected"
    assert "app_path" not in engine_rows[0]
    assert "app_url" not in engine_rows[0]
    assert "version" not in engine_rows[0]


def test_report_options_view_lists_current_views_and_columns() -> None:
    fake_console = FakeConsole()

    with patch.object(security_cli, "_console", return_value=fake_console):
        security_cli.report(view="options")

    assert len(fake_console.renderables) == 1
    output = str(fake_console.renderables[0])
    assert "app-summary" in output
    assert "apps" in output
    assert "engines" in output
    assert "stats" in output
    assert "scan_summary_available" in output
    assert "engine_category" in output


def test_report_apps_csv_prints_raw_app_metadata_csv() -> None:
    fake_console = FakeConsole()
    app_rows, engine_rows = _build_sample_report_rows()

    with (
        patch.object(security_cli, "_console", return_value=fake_console),
        patch("machineconfig.jobs.installer.checks.install_utils.load_app_metadata_report", return_value=app_rows),
        patch("machineconfig.jobs.installer.checks.install_utils.load_engine_results_report", return_value=engine_rows),
    ):
        security_cli.report(view="apps", format_type="csv")

    assert len(fake_console.renderables) == 1
    output = str(fake_console.renderables[0])
    assert "app_name,version,scan_time,app_path,app_url,scan_summary_available,notes" in output
    assert "zellij,v0.43.1,2026-03-17 06:05,~/.local/bin/zellij,https://example.test/zellij,True,All reporting engines returned a verdict." in output


def test_report_engines_csv_prints_raw_engine_csv() -> None:
    fake_console = FakeConsole()
    app_rows, engine_rows = _build_sample_report_rows()

    with (
        patch.object(security_cli, "_console", return_value=fake_console),
        patch("machineconfig.jobs.installer.checks.install_utils.load_app_metadata_report", return_value=app_rows),
        patch("machineconfig.jobs.installer.checks.install_utils.load_engine_results_report", return_value=engine_rows),
    ):
        security_cli.report(view="engines", format_type="csv")

    assert len(fake_console.renderables) == 1
    output = str(fake_console.renderables[0])
    assert "app_name,engine_name,engine_category,engine_result" in output
    assert "zellij,engine-a,harmless,clean" in output
    assert "zellij,engine-b,undetected," in output


def test_security_cli_help_shows_report_and_hides_legacy_summary_command() -> None:
    runner = CliRunner()
    result = runner.invoke(security_cli.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "Show saved scan results, CSV rows, or summary stats" in result.stdout
    assert "Scan installed apps or a single file path with VirusTotal" in result.stdout
    assert "scan-path" not in result.stdout
    assert "Show summary statistics for the last report" not in result.stdout


def test_security_cli_report_help_shows_view_choices() -> None:
    runner = CliRunner()
    result = runner.invoke(security_cli.get_app(), ["report", "--help"])

    assert result.exit_code == 0
    assert "--view" in result.stdout
    assert "--format" in result.stdout
    assert "app-summary" in result.stdout
    assert "apps" in result.stdout
    assert "engines" in result.stdout
    assert "stats" in result.stdout


def test_security_cli_scan_help_shows_path_and_record_options() -> None:
    runner = CliRunner()
    result = runner.invoke(security_cli.get_app(), ["scan", "--help"])

    assert result.exit_code == 0
    assert "--path" in result.stdout
    assert "--record" in result.stdout
    assert "--no-record" in result.stdout
    assert "installed-app scans" in result.stdout
    assert "disabled for --path" in result.stdout


def test_scan_impl_rejects_apps_and_path_together(tmp_path: Path) -> None:
    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"test")

    try:
        security_cli.run_scan(apps="zellij", path=sample_path, record=None)
    except Exception as exc:
        assert isinstance(exc, security_cli.typer.BadParameter)
        assert "Use either APPS or --path, not both." in str(exc)
    else:
        raise AssertionError("Expected BadParameter when APPS and --path are both provided.")


def test_scan_impl_path_defaults_to_not_writing_reports(tmp_path: Path) -> None:
    fake_console = FakeConsole()

    class FakeClientContext:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
            return None

    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"test")
    scan_summary: vt_utils.ScanSummary = {
        "positive_pct": 0.0,
        "total_engines": 2,
        "verdict_engines": 2,
        "flagged_engines": 0,
        "malicious_engines": 0,
        "suspicious_engines": 0,
        "harmless_engines": 1,
        "undetected_engines": 1,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": "All reporting engines returned a verdict.",
    }

    with (
        patch.object(security_cli, "_console", return_value=fake_console),
        patch("machineconfig.jobs.installer.checks.vt_utils.get_vt_client", return_value=FakeClientContext()),
        patch("machineconfig.jobs.installer.checks.vt_utils.scan_file", return_value=(scan_summary, [])),
        patch("machineconfig.jobs.installer.checks.check_installations.write_reports") as write_reports_mock,
    ):
        security_cli.run_scan(apps=None, path=sample_path, record=None)

    write_reports_mock.assert_not_called()
    output = "\n".join(str(renderable) for renderable in fake_console.renderables)
    assert "sample.bin: 0/2 flagged (0.0%)" in output
    assert "Scan results were not saved to the repo reports." in output


def test_scan_impl_path_records_results_when_requested(tmp_path: Path) -> None:
    fake_console = FakeConsole()

    class FakeClientContext:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
            return None

    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"test")
    scan_summary: vt_utils.ScanSummary = {
        "positive_pct": 50.0,
        "total_engines": 2,
        "verdict_engines": 2,
        "flagged_engines": 1,
        "malicious_engines": 1,
        "suspicious_engines": 0,
        "harmless_engines": 1,
        "undetected_engines": 0,
        "unsupported_engines": 0,
        "timeout_engines": 0,
        "failure_engines": 0,
        "other_engines": 0,
        "notes": "All reporting engines returned a verdict.",
    }
    scan_record: ScannedAppRecord = {
        "app_data": {
            "app_name": "sample",
            "version": None,
            "positive_pct": 50.0,
            "flagged_engines": 1,
            "verdict_engines": 2,
            "total_engines": 2,
            "malicious_engines": 1,
            "suspicious_engines": 0,
            "harmless_engines": 1,
            "undetected_engines": 0,
            "unsupported_engines": 0,
            "timeout_engines": 0,
            "failure_engines": 0,
            "other_engines": 0,
            "notes": "All reporting engines returned a verdict.",
            "scan_time": "2026-03-17 07:35",
            "app_path": str(sample_path),
            "app_url": "",
        },
        "engine_results": [{"app_name": "sample", "engine_name": "engine-a", "engine_category": "malicious", "engine_result": "test"}],
    }

    with (
        patch.object(security_cli, "_console", return_value=fake_console),
        patch("machineconfig.jobs.installer.checks.vt_utils.get_vt_client", return_value=FakeClientContext()),
        patch("machineconfig.jobs.installer.checks.vt_utils.scan_file", return_value=(scan_summary, [])),
        patch("machineconfig.jobs.installer.checks.check_installations.build_scan_record", return_value=scan_record) as build_scan_record_mock,
        patch(
            "machineconfig.jobs.installer.checks.check_installations.write_reports",
            return_value=(Path("/tmp/apps_metadata_report.csv"), Path("/tmp/apps_engine_results_report.csv")),
        ) as write_reports_mock,
    ):
        security_cli.run_scan(apps=None, path=sample_path, record=True)

    build_scan_record_mock.assert_called_once()
    write_reports_mock.assert_called_once_with([scan_record])
    output = "\n".join(str(renderable) for renderable in fake_console.renderables)
    assert "App metadata CSV report saved to: /tmp/apps_metadata_report.csv" in output
    assert "Engine CSV report saved to: /tmp/apps_engine_results_report.csv" in output


def test_scan_impl_routes_installed_app_record_flag() -> None:
    with patch("machineconfig.jobs.installer.checks.check_installations.scan_installed_apps") as scan_installed_apps_mock:
        security_cli.run_scan(apps="zellij,bat", path=None, record=False)

    scan_installed_apps_mock.assert_called_once_with(["zellij", "bat"], write_reports_to_repo=False)
