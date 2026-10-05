from collections.abc import Callable, Generator
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from stackops.jobs.installer.checks import scan_execution
from stackops.jobs.installer.checks.scan_history import load_run
from stackops.jobs.installer.checks.scan_outcomes import ScanSuccess
from stackops.jobs.installer.checks.vt_account_stats import VirusTotalAccountStats
from stackops.jobs.installer.checks.vt_utils import ScanResult, summarize_scan_results
from stackops.jobs.installer.checks.vt_workers import ScannedFile
from stackops.secrets.readers import VirusTotalApiKey


def test_installed_scan_uploads_scanned_hash_and_saves_link_with_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    apps: list[tuple[Path, str | None]] = [(tmp_path / "alpha", "1"), (tmp_path / "beta", "2")]
    hashes = ["a" * 64, "b" * 64]
    credentials = (VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),)
    credential_reads = 0
    uploaded: list[tuple[Path, str | None]] = []
    records_root = tmp_path / "records"

    def read_dummy_keys() -> tuple[VirusTotalApiKey, ...]:
        nonlocal credential_reads
        credential_reads += 1
        return credentials

    def completed_scans(
        apps_to_scan: list[tuple[Path, str | None]],
        selected_credentials: tuple[VirusTotalApiKey, ...],
        concurrency: int | None,
        stats: VirusTotalAccountStats,
        on_result: Callable[[ScannedFile], None],
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == apps
        assert selected_credentials == credentials
        assert concurrency == 1
        assert len(stats.snapshots()) == 1
        for index in (1, 0):
            results: list[ScanResult] = [{"engine_name": "sample-engine", "category": "malicious" if index else "undetected", "result": None}]
            scanned_file = ScannedFile(
                index=index,
                path=apps[index][0],
                version=apps[index][1],
                outcome=ScanSuccess(
                    summary=summarize_scan_results(results),
                    results=results,
                    scanned_at=datetime(2026, 10, 5, tzinfo=UTC),
                    source="existing_report",
                    sha256=hashes[index],
                ),
            )
            on_result(scanned_file)
            yield scanned_file

    def upload_dummy_app(path: Path, expected_sha256: str | None) -> str:
        uploaded.append((path, expected_sha256))
        return f"""https://example.invalid/{path.name}/{expected_sha256}"""

    monkeypatch.setattr(scan_execution, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(scan_execution, "scan_files_with_vt", completed_scans)
    monkeypatch.setattr(scan_execution, "upload_app", upload_dummy_app)
    monkeypatch.setattr(scan_execution, "console", Console(file=StringIO(), width=120))

    returned = scan_execution.execute_scan(apps, scope="apps", requested=["alpha", "beta"], record=True, concurrency=1, records_root=records_root)

    assert credential_reads == 1
    assert uploaded == [(apps[1][0], hashes[1]), (apps[0][0], hashes[0])]
    assert [app_data["app_name"] for app_data in returned] == ["alpha", "beta"]
    saved = load_run(records_root, run_id=None)
    assert saved["status"] == "completed"
    assert [target["sha256"] for target in saved["targets"]] == hashes
    assert [target["version"] for target in saved["targets"]] == ["1", "2"]
    for index, target in enumerate(saved["targets"]):
        record = target["record"]
        assert record is not None
        assert record["app_data"]["app_url"] == f"""https://example.invalid/{apps[index][0].name}/{hashes[index]}"""
        assert record["app_data"]["version"] == apps[index][1]


def test_path_scan_does_not_upload_but_saves_scanned_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "sample.bin"
    sha256 = "c" * 64
    credentials = (VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),)
    credential_reads = 0
    records_root = tmp_path / "records"

    def read_dummy_keys() -> tuple[VirusTotalApiKey, ...]:
        nonlocal credential_reads
        credential_reads += 1
        return credentials

    def completed_scans(
        apps_to_scan: list[tuple[Path, str | None]],
        selected_credentials: tuple[VirusTotalApiKey, ...],
        concurrency: int | None,
        stats: VirusTotalAccountStats,
        on_result: Callable[[ScannedFile], None],
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == [(path, None)]
        assert selected_credentials == credentials
        assert concurrency is None
        assert len(stats.snapshots()) == 1
        results: list[ScanResult] = [{"engine_name": "sample-engine", "category": "undetected", "result": None}]
        scanned_file = ScannedFile(
            index=0,
            path=path,
            version=None,
            outcome=ScanSuccess(
                summary=summarize_scan_results(results),
                results=results,
                scanned_at=datetime(2026, 10, 5, tzinfo=UTC),
                source="submitted_file",
                sha256=sha256,
            ),
        )
        on_result(scanned_file)
        yield scanned_file

    def forbidden_upload(path: Path, expected_sha256: str | None) -> str:
        raise AssertionError(f"""Path scans must not upload {path} ({expected_sha256}).""")

    monkeypatch.setattr(scan_execution, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(scan_execution, "scan_files_with_vt", completed_scans)
    monkeypatch.setattr(scan_execution, "upload_app", forbidden_upload)
    monkeypatch.setattr(scan_execution, "console", Console(file=StringIO(), width=120))

    returned = scan_execution.execute_scan(
        [(path, None)], scope="path", requested=[str(path)], record=True, concurrency=None, records_root=records_root
    )

    assert credential_reads == 1
    assert returned[0]["app_url"] == ""
    saved = load_run(records_root, run_id=None)
    assert saved["status"] == "completed"
    assert saved["targets"][0]["sha256"] == sha256
    record = saved["targets"][0]["record"]
    assert record is not None
    assert record["app_data"]["app_url"] == ""
