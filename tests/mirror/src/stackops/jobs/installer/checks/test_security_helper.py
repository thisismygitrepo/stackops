import asyncio
import csv
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from threading import Event, Lock
from types import TracebackType
from typing import TYPE_CHECKING, Self, cast

import pytest
from rich.console import Console
import rich.console as rich_console
import typer

from stackops.jobs.installer.checks import check_installations, security_helper, vt_scanner, vt_utils
from stackops.jobs.installer.checks.scan_outcomes import ScanCancelled, ScanFailure, ScanOutcome, ScanSuccess
from stackops.secrets import readers
from stackops.secrets.readers import VirusTotalApiKey

if TYPE_CHECKING:
    import vt


class _Client:
    closed: bool = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, _exception_type: type[BaseException] | None, _exception: BaseException | None, _traceback: TracebackType | None
    ) -> None:
        self.closed = True


@pytest.mark.parametrize("record", [False, True])
@pytest.mark.parametrize("failed", [False, True])
def test_single_scan_uses_initialized_loop_and_saves_only_when_requested(
    record: bool, failed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    credentials = (VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),)
    client = _Client()
    output = StringIO()
    console = Console(file=output, width=200)
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

    def create_dummy_client(api_key: str) -> "vt.Client":
        assert api_key == "dummy-key"
        assert asyncio.get_event_loop().is_closed() is False
        return cast("vt.Client", client)

    def dummy_scan(path: Path, client: "vt.Client", stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert path == Path("rg")
        assert client is not None
        assert stop is None
        assert request_lock is None
        return outcome

    def create_console() -> Console:
        return console

    monkeypatch.setattr(readers, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(vt_utils, "get_vt_client", create_dummy_client)
    monkeypatch.setattr(vt_scanner, "scan_file", dummy_scan)
    monkeypatch.setattr(check_installations, "APP_METADATA_PATH", metadata_path)
    monkeypatch.setattr(check_installations, "ENGINE_RESULTS_PATH", engine_path)
    monkeypatch.setattr(rich_console, "Console", create_console)

    if failed:
        with pytest.raises(typer.Exit) as raised_exit:
            security_helper.scan_single_path(path=Path("rg"), record=record, apps_per_key=1)
        assert raised_exit.value.exit_code == 1
    else:
        security_helper.scan_single_path(path=Path("rg"), record=record, apps_per_key=1)

    assert client.closed
    displayed = output.getvalue()
    assert "Pending" not in displayed
    assert "dummy-key" not in displayed
    assert "dummy-account" not in displayed
    if failed:
        assert "Failed" in displayed
        assert "ForbiddenError" in displayed
        assert "1 of 1 VirusTotal scans failed" in displayed
    else:
        assert "Clean 0/1 (0.0%)" in displayed
        assert "Existing VirusTotal report." in displayed
    if record:
        with metadata_path.open(newline="") as metadata_file:
            metadata_rows = list(csv.DictReader(metadata_file))
        assert metadata_rows[0]["scan_summary_available"] == str(not failed)
        if failed:
            assert "ForbiddenError" in metadata_rows[0]["notes"]
            assert displayed.index("Engine CSV report saved") < displayed.index("1 of 1 VirusTotal scans failed")
    else:
        assert metadata_path.read_text(encoding="utf-8") == "original metadata"
        assert engine_path.read_text(encoding="utf-8") == "original engines"


def test_cancelled_single_scan_does_not_save_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = _Client()
    metadata_path = tmp_path / "metadata.csv"
    engine_path = tmp_path / "engines.csv"

    def read_dummy_keys() -> tuple[VirusTotalApiKey, ...]:
        return (VirusTotalApiKey(account_name="dummy-account", api_key="dummy-key"),)

    def create_dummy_client(api_key: str) -> "vt.Client":
        assert api_key == "dummy-key"
        return cast("vt.Client", client)

    def dummy_scan(path: Path, client: "vt.Client", stop: Event | None, request_lock: Lock | None) -> ScanOutcome:
        assert path == Path("rg")
        assert client is not None
        assert stop is None
        assert request_lock is None
        return ScanCancelled()

    monkeypatch.setattr(readers, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(vt_utils, "get_vt_client", create_dummy_client)
    monkeypatch.setattr(vt_scanner, "scan_file", dummy_scan)
    monkeypatch.setattr(check_installations, "APP_METADATA_PATH", metadata_path)
    monkeypatch.setattr(check_installations, "ENGINE_RESULTS_PATH", engine_path)

    with pytest.raises(typer.Exit) as raised_exit:
        security_helper.scan_single_path(path=Path("rg"), record=True, apps_per_key=1)

    assert raised_exit.value.exit_code == 1
    assert client.closed
    assert not metadata_path.exists()
    assert not engine_path.exists()
