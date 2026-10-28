import csv
import re
from collections.abc import Callable, Generator
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
import typer
from rich.console import Console

from stackops.jobs.installer.checks import scan_execution
from stackops.jobs.installer.checks.report_utils import ScannedAppRecord
from stackops.jobs.installer.checks.scan_history import ScanRun, load_run
from stackops.jobs.installer.checks.scan_outcomes import ScanFailure, ScanSuccess
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results
from stackops.jobs.installer.checks.vt_workers import ScannedFile
from stackops.secrets.readers import VirusTotalApiKey

type ScanFiles = Callable[
    [list[tuple[Path, str | None]], tuple[VirusTotalApiKey, ...], int | None, VirusTotalAccountStats, Callable[[ScannedFile], None]],
    Generator[ScannedFile, None, None],
]

ACCOUNT_REPORT_TITLE = "VirusTotal Account Request Statistics"
SAMPLE_RESULTS: list[ScanResult] = [{"engine_name": "sample-engine", "category": "undetected", "result": None}]


def _credentials(count: int) -> tuple[VirusTotalApiKey, ...]:
    return tuple(VirusTotalApiKey(account_name=f"""dummy-account-{index}""", api_key=f"""dummy-key-{index}""") for index in range(count))


def _install_fakes(
    monkeypatch: pytest.MonkeyPatch,
    credentials: tuple[VirusTotalApiKey, ...],
    scans: ScanFiles,
    uploader: Callable[[Path, str | None], str],
    output: StringIO,
) -> None:
    def read_dummy_keys() -> tuple[VirusTotalApiKey, ...]:
        return credentials

    monkeypatch.setattr(scan_execution, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(scan_execution, "scan_files_with_vt", scans)
    monkeypatch.setattr(scan_execution, "upload_app", uploader)
    monkeypatch.setattr(scan_execution, "console", Console(file=output, width=220))


def _record(saved: ScanRun, index: int) -> ScannedAppRecord:
    record = saved["targets"][index]["record"]
    assert record is not None
    return record


def _account_rows(saved: ScanRun) -> list[dict[str, str]]:
    return list(csv.DictReader(StringIO(saved["account_csv"])))


@pytest.mark.parametrize("api_key_count", [1, 3])
def test_parallel_results_keep_app_metadata_and_input_order(api_key_count: int, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    apps: list[tuple[Path, str | None]] = [(Path("alpha"), "1"), (Path("beta"), "2")]
    credentials = _credentials(api_key_count)
    hashes = ["a" * 64, "b" * 64]
    engine_results: list[list[ScanResult]] = [
        [{"engine_name": "alpha-engine", "category": "undetected", "result": None}],
        [{"engine_name": "beta-engine", "category": "malicious", "result": "dummy-detection"}],
    ]
    uploaded: list[tuple[Path, str | None]] = []
    output = StringIO()
    records_root = tmp_path / "records"

    def completed_scans(
        apps_to_scan: list[tuple[Path, str | None]],
        selected_credentials: tuple[VirusTotalApiKey, ...],
        concurrency: int | None,
        stats: VirusTotalAccountStats,
        on_result: Callable[[ScannedFile], None],
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == apps
        assert len(selected_credentials) == api_key_count
        assert concurrency == 2
        assert len(stats.snapshots()) == api_key_count
        for index in (1, 0):
            scanned_file = ScannedFile(
                index=index,
                path=apps[index][0],
                version=apps[index][1],
                outcome=ScanSuccess(
                    summary=summarize_scan_results(engine_results[index]),
                    results=engine_results[index],
                    scanned_at=datetime(2026, 10, 4, 6, 44, tzinfo=UTC),
                    source="submitted_file",
                    sha256=hashes[index],
                ),
            )
            on_result(scanned_file)
            yield scanned_file

    def upload_dummy_app(path: Path, expected_sha256: str | None) -> str:
        uploaded.append((path, expected_sha256))
        return f"""https://example.invalid/{path.name}"""

    _install_fakes(monkeypatch, credentials, completed_scans, upload_dummy_app, output)

    returned = scan_execution.execute_scan(
        apps, scope="apps", requested=["alpha", "beta"], record=True, upload=True, concurrency=2, records_root=records_root
    )

    assert uploaded == [(Path("beta"), hashes[1]), (Path("alpha"), hashes[0])]
    assert [app_data["app_name"] for app_data in returned] == ["alpha", "beta"]
    assert [app_data["version"] for app_data in returned] == ["1", "2"]
    assert [app_data["positive_pct"] for app_data in returned] == [0.0, 100.0]
    assert [app_data["app_url"] for app_data in returned] == ["https://example.invalid/alpha", "https://example.invalid/beta"]
    saved = load_run(records_root, run_id=None)
    assert [_record(saved, index)["engine_results"][0]["engine_name"] for index in range(2)] == ["alpha-engine", "beta-engine"]
    displayed = output.getvalue()
    assert re.search(rf"""Configured accounts\s+{api_key_count}""", displayed)
    assert re.search(r"Concurrent files \(maximum\)\s+2", displayed)
    assert "Account request pacing" in displayed
    before_account_report = displayed.split(ACCOUNT_REPORT_TITLE)[0]
    assert all(credential.api_key not in displayed and credential.account_name not in before_account_report for credential in credentials)


def test_empty_scan_never_reads_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    records_root = tmp_path / "records"

    def forbidden_read() -> tuple[VirusTotalApiKey, ...]:
        raise AssertionError("An empty scan must not load credentials.")

    monkeypatch.setattr(scan_execution, "read_virus_total_api_keys", forbidden_read)
    monkeypatch.setattr(scan_execution, "console", Console(file=StringIO(), width=220))

    with pytest.raises(typer.Exit) as raised_exit:
        scan_execution.execute_scan([], scope="all", requested=[], record=True, upload=False, concurrency=None, records_root=records_root)

    assert raised_exit.value.exit_code == 1
    saved = load_run(records_root, run_id=None)
    assert saved["status"] == "empty"
    assert saved["targets"] == []


def test_invalid_credentials_fail_the_scan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    records_root = tmp_path / "records"

    def invalid_credentials() -> tuple[VirusTotalApiKey, ...]:
        raise ValueError("Invalid dummy credentials.")

    monkeypatch.setattr(scan_execution, "read_virus_total_api_keys", invalid_credentials)
    monkeypatch.setattr(scan_execution, "console", Console(file=StringIO(), width=220))

    with pytest.raises(ValueError, match="Invalid dummy credentials"):
        scan_execution.execute_scan(
            [(Path("alpha"), None)], scope="all", requested=[], record=True, upload=False, concurrency=None, records_root=records_root
        )

    saved = load_run(records_root, run_id=None)
    assert saved["status"] == "failed"
    assert saved["message"] == "VirusTotal credential loading failed (ValueError)."
    assert saved["targets"][0]["record"] is None


def test_mixed_scan_saves_errors_and_results_before_failing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    apps: list[tuple[Path, str | None]] = [(Path("alpha"), "1"), (Path("beta"), "2")]
    credentials = _credentials(1)
    hashes = ["a" * 64, "b" * 64]
    scanned_at = datetime(2026, 10, 3, 1, 2, tzinfo=UTC)
    uploaded: list[tuple[Path, str | None]] = []
    output = StringIO()
    records_root = tmp_path / "records"

    def completed_scans(
        apps_to_scan: list[tuple[Path, str | None]],
        selected_credentials: tuple[VirusTotalApiKey, ...],
        concurrency: int | None,
        stats: VirusTotalAccountStats,
        on_result: Callable[[ScannedFile], None],
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == apps
        assert len(selected_credentials) == 1
        assert concurrency == 1
        stats.request_started(0)
        stats.failed(0, "report lookup", "QuotaExceededError")
        stats.disabled(0, "QuotaExceededError")
        failed_file = ScannedFile(
            index=0,
            path=apps[0][0],
            version=apps[0][1],
            outcome=ScanFailure(stage="report lookup", error_type="APIError", error_code="QuotaExceededError", sha256=hashes[0]),
        )
        on_result(failed_file)
        yield failed_file
        stats.request_started(0)
        stats.succeeded(0)
        succeeded_file = ScannedFile(
            index=1,
            path=apps[1][0],
            version=apps[1][1],
            outcome=ScanSuccess(
                summary=summarize_scan_results(SAMPLE_RESULTS),
                results=SAMPLE_RESULTS,
                scanned_at=scanned_at,
                source="existing_report",
                sha256=hashes[1],
            ),
        )
        on_result(succeeded_file)
        yield succeeded_file

    def upload_dummy_app(path: Path, expected_sha256: str | None) -> str:
        uploaded.append((path, expected_sha256))
        return f"""https://example.invalid/{path.name}"""

    _install_fakes(monkeypatch, credentials, completed_scans, upload_dummy_app, output)

    with pytest.raises(typer.Exit) as raised_exit:
        scan_execution.execute_scan(
            apps, scope="apps", requested=["alpha", "beta"], record=True, upload=True, concurrency=1, records_root=records_root
        )

    assert raised_exit.value.exit_code == 1
    assert uploaded == [(Path("beta"), hashes[1])]
    saved = load_run(records_root, run_id=None)
    assert saved["status"] == "completed_with_errors"
    assert saved["message"] == "1 of 2 VirusTotal scans failed."
    assert [_record(saved, index)["app_data"]["app_name"] for index in range(2)] == ["alpha", "beta"]
    failed_data, succeeded_data = _record(saved, 0)["app_data"], _record(saved, 1)["app_data"]
    assert failed_data["positive_pct"] is None
    assert "QuotaExceededError" in failed_data["notes"]
    assert "report lookup" in failed_data["notes"]
    assert failed_data["app_url"] == ""
    assert saved["targets"][0]["error"] == {"stage": "report lookup", "error_type": "APIError", "error_code": "QuotaExceededError"}
    assert [target["sha256"] for target in saved["targets"]] == hashes
    assert succeeded_data["scan_time"] == scanned_at.isoformat()
    assert succeeded_data["notes"].startswith("Existing VirusTotal report. ")
    assert succeeded_data["app_url"] == "https://example.invalid/beta"
    assert saved["targets"][1]["source"] == "existing_report"
    assert _record(saved, 0)["engine_results"] == []
    assert [row["engine_name"] for row in _record(saved, 1)["engine_results"]] == ["sample-engine"]
    displayed = output.getvalue()
    assert "Failed" in displayed
    assert "Pending" not in displayed
    assert displayed.index("1 of 2 VirusTotal scans failed") < displayed.index(ACCOUNT_REPORT_TITLE) < displayed.index("Scan run saved")
    assert "dummy-account-0" in displayed
    assert "dummy-key-0" not in displayed
    account_rows = _account_rows(saved)
    assert account_rows[0]["account_name"] == "dummy-account-0"
    assert account_rows[0]["requests"] == "2"
    assert account_rows[0]["failed"] == "1"
