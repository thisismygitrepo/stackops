import csv
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


def _forbidden_upload(path: Path, expected_sha256: str | None) -> str:
    raise AssertionError("Uploads are disabled for this scan.")


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


@pytest.mark.parametrize("record", [False, True])
@pytest.mark.parametrize("failed", [False, True])
def test_single_scan_uses_account_pool_and_saves_only_when_requested(
    record: bool, failed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credentials = _credentials(2)
    output = StringIO()
    records_root = tmp_path / "records"
    outcome: ScanSuccess | ScanFailure = (
        ScanFailure(stage="report lookup", error_type="APIError", error_code="ForbiddenError", sha256="c" * 64)
        if failed
        else ScanSuccess(
            summary=summarize_scan_results(SAMPLE_RESULTS),
            results=SAMPLE_RESULTS,
            scanned_at=datetime(2026, 10, 3, 1, 2, tzinfo=UTC),
            source="existing_report",
            sha256="c" * 64,
        )
    )

    def completed_scans(
        apps_to_scan: list[tuple[Path, str | None]],
        selected_credentials: tuple[VirusTotalApiKey, ...],
        concurrency: int | None,
        stats: VirusTotalAccountStats,
        on_result: Callable[[ScannedFile], None],
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == [(Path("rg"), None)]
        assert len(selected_credentials) == 2
        assert concurrency == 4
        stats.request_started(0)
        if failed:
            stats.failed(0, "report lookup", "ForbiddenError")
            stats.disabled(0, "ForbiddenError")
        else:
            stats.succeeded(0)
        scanned_file = ScannedFile(index=0, path=Path("rg"), version=None, outcome=outcome)
        on_result(scanned_file)
        yield scanned_file

    _install_fakes(monkeypatch, credentials, completed_scans, _forbidden_upload, output)

    def run_single_scan() -> None:
        scan_execution.execute_scan(
            [(Path("rg"), None)], scope="path", requested=["rg"], record=record, upload=False, concurrency=4, records_root=records_root
        )

    if failed:
        with pytest.raises(typer.Exit) as raised_exit:
            run_single_scan()
        assert raised_exit.value.exit_code == 1
    else:
        run_single_scan()

    displayed = output.getvalue()
    assert "Pending" not in displayed
    assert all(credential.api_key not in displayed for credential in credentials)
    assert all(credential.account_name in displayed for credential in credentials)
    assert ACCOUNT_REPORT_TITLE in displayed
    if failed:
        assert "Failed" in displayed
        assert "ForbiddenError" in displayed
        assert "1 of 1 VirusTotal scans failed" in displayed
        assert displayed.index("1 of 1 VirusTotal scans failed") < displayed.index(ACCOUNT_REPORT_TITLE)
    else:
        assert "Clean 0/1 (0.0%)" in displayed
        assert "Existing VirusTotal report." in displayed
    if record:
        saved = load_run(records_root, run_id=None)
        assert saved["scope"] == "path"
        assert (_record(saved, 0)["app_data"]["positive_pct"] is not None) == (not failed)
        account_rows = _account_rows(saved)
        assert account_rows[0]["requests"] == "1"
        assert account_rows[0]["failed"] == str(int(failed))
        assert account_rows[1]["requests"] == "0"
    else:
        assert not records_root.exists()


def test_worker_error_still_reports_accounts_without_saving_app_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    credentials = _credentials(1)
    output = StringIO()
    records_root = tmp_path / "records"

    def stopped_scans(
        apps_to_scan: list[tuple[Path, str | None]],
        selected_credentials: tuple[VirusTotalApiKey, ...],
        concurrency: int | None,
        stats: VirusTotalAccountStats,
        on_result: Callable[[ScannedFile], None],
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == [(Path("rg"), None)]
        assert len(selected_credentials) == 1
        assert concurrency is None
        stats.request_started(0)
        stats.failed(0, "report lookup", "ConnectionError")
        yield from ()
        raise RuntimeError("VirusTotal worker failed.")

    _install_fakes(monkeypatch, credentials, stopped_scans, _forbidden_upload, output)

    with pytest.raises(RuntimeError, match="VirusTotal worker failed"):
        scan_execution.execute_scan(
            [(Path("rg"), None)], scope="path", requested=["rg"], record=True, upload=False, concurrency=None, records_root=records_root
        )

    saved = load_run(records_root, run_id=None)
    assert saved["status"] == "failed"
    assert saved["message"] == "VirusTotal scanning failed (RuntimeError)."
    assert saved["targets"][0]["record"] is None
    displayed = output.getvalue()
    assert ACCOUNT_REPORT_TITLE in displayed
    assert "ConnectionError" in displayed
    assert "dummy-key-0" not in displayed
    assert _account_rows(saved)[0]["account_name"] == "dummy-account-0"
