from collections.abc import Generator
import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
import re

import pytest
import typer
from rich.console import Console

from stackops.jobs.installer.checks import check_installations
from stackops.jobs.installer.checks.scan_outcomes import ScanFailure, ScanSuccess
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results
from stackops.jobs.installer.checks.vt_workers import ScannedFile
from stackops.secrets.readers import VirusTotalApiKey


@pytest.mark.parametrize("api_key_count", [1, 3])
def test_parallel_results_keep_app_metadata_and_input_order(api_key_count: int, monkeypatch: pytest.MonkeyPatch) -> None:
    apps = [(Path("alpha"), "1"), (Path("beta"), "2")]
    credentials = tuple(
        VirusTotalApiKey(account_name=f"""dummy-account-{index}""", api_key=f"""dummy-key-{index}""") for index in range(api_key_count)
    )
    alpha_results: list[ScanResult] = [{"engine_name": "alpha-engine", "category": "undetected", "result": None}]
    beta_results: list[ScanResult] = [{"engine_name": "beta-engine", "category": "malicious", "result": "dummy-detection"}]
    uploaded: list[Path] = []
    output = StringIO()

    def read_dummy_keys() -> tuple[VirusTotalApiKey, ...]:
        return credentials

    def completed_scans(
        apps_to_scan: list[tuple[Path, str | None]], credentials: tuple[VirusTotalApiKey, ...], concurrency: int | None, stats: VirusTotalAccountStats
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == apps
        assert len(credentials) == api_key_count
        assert concurrency == 2
        assert len(stats.snapshots()) == api_key_count
        for index, results in [(1, beta_results), (0, alpha_results)]:
            yield ScannedFile(
                index=index,
                path=apps[index][0],
                version=apps[index][1],
                outcome=ScanSuccess(
                    summary=summarize_scan_results(results),
                    results=results,
                    scanned_at=datetime(2026, 10, 4, 6, 44, tzinfo=UTC),
                    source="submitted_file",
                ),
            )

    def upload_dummy_app(path: Path) -> str:
        uploaded.append(path)
        return f"""https://example.invalid/{path.name}"""

    monkeypatch.setattr(check_installations, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(check_installations, "scan_files_with_vt", completed_scans)
    monkeypatch.setattr(check_installations, "upload_app", upload_dummy_app)
    monkeypatch.setattr(check_installations, "console", Console(file=output, width=120))

    records = check_installations.scan_apps_with_vt(
        apps, concurrency=2, credentials=credentials, stats=VirusTotalAccountStats(tuple(credential.account_name for credential in credentials))
    )

    assert uploaded == [Path("beta"), Path("alpha")]
    assert [record["app_data"]["app_name"] for record in records] == ["alpha", "beta"]
    assert [record["app_data"]["version"] for record in records] == ["1", "2"]
    assert [record["app_data"]["positive_pct"] for record in records] == [0.0, 100.0]
    assert [record["app_data"]["app_url"] for record in records] == ["https://example.invalid/alpha", "https://example.invalid/beta"]
    assert [record["engine_results"][0]["engine_name"] for record in records] == ["alpha-engine", "beta-engine"]
    displayed = output.getvalue()
    assert re.search(rf"""Configured accounts\s+{api_key_count}""", displayed)
    assert re.search(r"Concurrent files \(maximum\)\s+2", displayed)
    assert "Account request pacing" in displayed
    assert all(credential.api_key not in displayed and credential.account_name not in displayed for credential in credentials)


def test_empty_scan_never_reads_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_read() -> tuple[VirusTotalApiKey, ...]:
        raise AssertionError("An empty scan must not load credentials.")

    monkeypatch.setattr(check_installations, "read_virus_total_api_keys", forbidden_read)

    assert check_installations.scan_apps_with_vt([], concurrency=None, credentials=(), stats=VirusTotalAccountStats(())) == []


def test_invalid_credentials_fail_the_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    def collect_dummy_apps(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
        assert app_names is None
        return [(Path("alpha"), None)]

    def invalid_credentials() -> tuple[VirusTotalApiKey, ...]:
        raise ValueError("Invalid dummy credentials.")

    monkeypatch.setattr(check_installations, "read_virus_total_api_keys", invalid_credentials)
    monkeypatch.setattr(check_installations, "collect_apps_to_scan", collect_dummy_apps)

    with pytest.raises(ValueError, match="Invalid dummy credentials"):
        check_installations.scan_installed_apps(app_names=None, write_reports_to_repo=False, concurrency=None)


def test_mixed_scan_saves_errors_and_results_before_failing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    apps = [(Path("alpha"), "1"), (Path("beta"), "2")]
    credentials = (VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),)
    results: list[ScanResult] = [{"engine_name": "sample-engine", "category": "undetected", "result": None}]
    uploaded: list[Path] = []
    output = StringIO()
    metadata_path = tmp_path / "metadata.csv"
    engine_path = tmp_path / "engines.csv"

    def collect_dummy_apps(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
        assert app_names == ["alpha", "beta"]
        return apps

    def read_dummy_keys() -> tuple[VirusTotalApiKey, ...]:
        return credentials

    def completed_scans(
        apps_to_scan: list[tuple[Path, str | None]], credentials: tuple[VirusTotalApiKey, ...], concurrency: int | None, stats: VirusTotalAccountStats
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == apps
        assert len(credentials) == 1
        assert concurrency == 1
        stats.request_started(0)
        stats.failed(0, "report lookup", "QuotaExceededError")
        stats.disabled(0, "QuotaExceededError")
        yield ScannedFile(
            index=0,
            path=apps[0][0],
            version=apps[0][1],
            outcome=ScanFailure(stage="report lookup", error_type="APIError", error_code="QuotaExceededError"),
        )
        stats.request_started(0)
        stats.succeeded(0)
        yield ScannedFile(
            index=1,
            path=apps[1][0],
            version=apps[1][1],
            outcome=ScanSuccess(
                summary=summarize_scan_results(results),
                results=results,
                scanned_at=datetime(2026, 10, 3, 1, 2, tzinfo=UTC),
                source="existing_report",
            ),
        )

    def upload_dummy_app(path: Path) -> str:
        uploaded.append(path)
        return f"""https://example.invalid/{path.name}"""

    monkeypatch.setattr(check_installations, "collect_apps_to_scan", collect_dummy_apps)
    monkeypatch.setattr(check_installations, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(check_installations, "scan_files_with_vt", completed_scans)
    monkeypatch.setattr(check_installations, "upload_app", upload_dummy_app)
    monkeypatch.setattr(check_installations, "APP_METADATA_PATH", metadata_path)
    monkeypatch.setattr(check_installations, "ENGINE_RESULTS_PATH", engine_path)
    monkeypatch.setattr(check_installations, "console", Console(file=output, width=220))

    with pytest.raises(typer.Exit) as raised_exit:
        check_installations.scan_installed_apps(app_names=["alpha", "beta"], write_reports_to_repo=True, concurrency=1)

    assert raised_exit.value.exit_code == 1
    assert uploaded == [Path("beta")]
    with metadata_path.open(newline="") as metadata_file:
        metadata_rows = list(csv.DictReader(metadata_file))
    with engine_path.open(newline="") as engine_file:
        engine_rows = list(csv.DictReader(engine_file))
    assert [row["app_name"] for row in metadata_rows] == ["alpha", "beta"]
    assert metadata_rows[0]["scan_summary_available"] == "False"
    assert "QuotaExceededError" in metadata_rows[0]["notes"]
    assert "report lookup" in metadata_rows[0]["notes"]
    assert metadata_rows[0]["app_url"] == ""
    assert metadata_rows[1]["scan_time"] == datetime(2026, 10, 3, 1, 2, tzinfo=UTC).astimezone().strftime("%Y-%m-%d %H:%M")
    assert metadata_rows[1]["notes"].startswith("Existing VirusTotal report. ")
    assert [row["app_name"] for row in engine_rows] == ["beta"]
    displayed = output.getvalue()
    assert "1 of 2 VirusTotal scans failed" in displayed
    assert "Failed" in displayed
    assert "Pending" not in displayed
    assert displayed.index("Engine CSV report saved") < displayed.index("1 of 2 VirusTotal scans failed")
    assert displayed.index("1 of 2 VirusTotal scans failed") < displayed.index("VirusTotal Account Request Statistics")
    assert "dummy-account" in displayed
    assert "dummy-key" not in displayed
    with (tmp_path / "apps_vt_accounts_report.csv").open(newline="") as account_file:
        account_rows = list(csv.DictReader(account_file))
    assert account_rows[0]["account_name"] == "dummy-account"
    assert account_rows[0]["requests"] == "2"
    assert account_rows[0]["failed"] == "1"
