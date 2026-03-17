from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

from machineconfig.jobs.installer.checks import check_installations, security_cli, vt_utils
from machineconfig.utils.path_extended import PathExtended

if TYPE_CHECKING:
    import vt


def test_summarize_scan_results_uses_only_flagging_categories_for_positive_pct() -> None:
    results: list[vt_utils.ScanResult] = [
        {"category": "undetected", "result": None},
        {"category": "harmless", "result": "clean"},
        {"category": "suspicious", "result": "heuristic match"},
        {"category": "timeout", "result": None},
        {"category": "type-unsupported", "result": None},
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
        {"category": "undetected", "result": None},
        {"category": "suspicious", "result": "heuristic"},
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
        app_data_list = check_installations.scan_apps_with_vt([(PathExtended("/tmp/zellij"), "v0.43.1")])

    assert fake_client.closed is True
    assert len(app_data_list) == 1
    assert app_data_list[0]["positive_pct"] == 1.4
    assert app_data_list[0]["flagged_engines"] == 1
    assert app_data_list[0]["verdict_engines"] == 72
    assert app_data_list[0]["notes"] == "All reporting engines returned a verdict."


def test_to_app_data_list_backfills_legacy_report_fields() -> None:
    rows: list[dict[str, object]] = [
        {
            "app_name": "zellij",
            "version": "v0.43.1",
            "positive_pct": "0.0",
            "scan_time": "2026-03-17 06:05",
            "app_path": "~/.local/bin/zellij",
            "app_url": "https://example.test/zellij",
        }
    ]

    app_data_list = security_cli.to_app_data_list(rows)

    assert len(app_data_list) == 1
    assert app_data_list[0]["flagged_engines"] == 0
    assert app_data_list[0]["verdict_engines"] == 0
    assert app_data_list[0]["total_engines"] == 0
    assert app_data_list[0]["notes"] == ""
