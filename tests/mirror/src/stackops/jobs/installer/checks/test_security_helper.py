from collections.abc import Generator
import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
import rich.console as rich_console
import typer

from stackops.jobs.installer.checks import check_installations, security_helper, vt_utils, vt_workers
from stackops.jobs.installer.checks.scan_outcomes import ScanFailure, ScanSuccess
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_workers import ScannedFile
from stackops.secrets import readers
from stackops.secrets.readers import VirusTotalApiKey


@pytest.mark.parametrize("record", [False, True])
@pytest.mark.parametrize("failed", [False, True])
def test_single_scan_uses_account_pool_and_saves_only_when_requested(
    record: bool, failed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credentials = (
        VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),
        VirusTotalApiKey(account_name="second-account", api_key="second-key"),
    )
    output = StringIO()
    console = Console(file=output, width=220)
    metadata_path = tmp_path / "metadata.csv"
    engine_path = tmp_path / "engines.csv"
    metadata_path.write_text("original metadata", encoding="utf-8")
    engine_path.write_text("original engines", encoding="utf-8")
    results: list[vt_utils.ScanResult] = [{"engine_name": "sample-engine", "category": "undetected", "result": None}]
    outcome: ScanSuccess | ScanFailure = (
        ScanFailure(stage="report lookup", error_type="APIError", error_code="ForbiddenError")
        if failed
        else ScanSuccess(
            summary=vt_utils.summarize_scan_results(results),
            results=results,
            scanned_at=datetime(2026, 10, 3, 1, 2, tzinfo=UTC),
            source="existing_report",
        )
    )

    def read_dummy_keys() -> tuple[VirusTotalApiKey, ...]:
        return credentials

    def completed_scans(
        apps_to_scan: list[tuple[Path, str | None]],
        credentials: tuple[VirusTotalApiKey, ...],
        concurrency: int | None,
        stats: VirusTotalAccountStats,
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == [(Path("rg"), None)]
        assert len(credentials) == 2
        assert concurrency == 4
        stats.request_started(0)
        if failed:
            stats.failed(0, "report lookup", "ForbiddenError")
            stats.disabled(0, "ForbiddenError")
        else:
            stats.succeeded(0)
        yield ScannedFile(index=0, path=Path("rg"), version=None, outcome=outcome)

    def create_console() -> Console:
        return console

    monkeypatch.setattr(readers, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(vt_workers, "scan_files_with_vt", completed_scans)
    monkeypatch.setattr(check_installations, "APP_METADATA_PATH", metadata_path)
    monkeypatch.setattr(check_installations, "ENGINE_RESULTS_PATH", engine_path)
    monkeypatch.setattr(rich_console, "Console", create_console)

    if failed:
        with pytest.raises(typer.Exit) as raised_exit:
            security_helper.scan_single_path(path=Path("rg"), record=record, concurrency=4)
        assert raised_exit.value.exit_code == 1
    else:
        security_helper.scan_single_path(path=Path("rg"), record=record, concurrency=4)

    displayed = output.getvalue()
    assert "Pending" not in displayed
    assert all(credential.api_key not in displayed for credential in credentials)
    assert all(credential.account_name in displayed for credential in credentials)
    assert "VirusTotal Account Request Statistics" in displayed
    if failed:
        assert "Failed" in displayed
        assert "ForbiddenError" in displayed
        assert "1 of 1 VirusTotal scans failed" in displayed
        assert displayed.index("1 of 1 VirusTotal scans failed") < displayed.index("VirusTotal Account Request Statistics")
    else:
        assert "Clean 0/1 (0.0%)" in displayed
        assert "Existing VirusTotal report." in displayed
    account_path = tmp_path / "apps_vt_accounts_report.csv"
    if record:
        with metadata_path.open(newline="") as metadata_file:
            metadata_rows = list(csv.DictReader(metadata_file))
        assert metadata_rows[0]["scan_summary_available"] == str(not failed)
        with account_path.open(newline="") as account_file:
            account_rows = list(csv.DictReader(account_file))
        assert account_rows[0]["requests"] == "1"
        assert account_rows[0]["failed"] == str(int(failed))
        assert account_rows[1]["requests"] == "0"
    else:
        assert metadata_path.read_text(encoding="utf-8") == "original metadata"
        assert engine_path.read_text(encoding="utf-8") == "original engines"
        assert not account_path.exists()


def test_worker_error_still_reports_accounts_without_saving_app_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    metadata_path = tmp_path / "metadata.csv"
    engine_path = tmp_path / "engines.csv"
    output = StringIO()
    console = Console(file=output, width=220)

    def read_dummy_keys() -> tuple[VirusTotalApiKey, ...]:
        return (VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),)

    def stopped_scans(
        apps_to_scan: list[tuple[Path, str | None]],
        credentials: tuple[VirusTotalApiKey, ...],
        concurrency: int | None,
        stats: VirusTotalAccountStats,
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == [(Path("rg"), None)]
        assert len(credentials) == 1
        assert concurrency is None
        stats.request_started(0)
        stats.failed(0, "report lookup", "ConnectionError")
        yield from ()
        raise RuntimeError("VirusTotal worker failed.")

    def create_console() -> Console:
        return console

    monkeypatch.setattr(readers, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(vt_workers, "scan_files_with_vt", stopped_scans)
    monkeypatch.setattr(check_installations, "APP_METADATA_PATH", metadata_path)
    monkeypatch.setattr(check_installations, "ENGINE_RESULTS_PATH", engine_path)
    monkeypatch.setattr(rich_console, "Console", create_console)

    with pytest.raises(RuntimeError, match="VirusTotal worker failed"):
        security_helper.scan_single_path(path=Path("rg"), record=True, concurrency=None)

    assert not metadata_path.exists()
    assert not engine_path.exists()
    assert "VirusTotal Account Request Statistics" in output.getvalue()
    assert "ConnectionError" in output.getvalue()
    assert "dummy-key" not in output.getvalue()
    assert (tmp_path / "apps_vt_accounts_report.csv").exists()
