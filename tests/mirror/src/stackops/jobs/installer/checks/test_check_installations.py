from collections.abc import Generator
from io import StringIO
from pathlib import Path
import re

import pytest
from rich.console import Console

from stackops.jobs.installer.checks import check_installations
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
        apps_to_scan: list[tuple[Path, str | None]], credentials: tuple[VirusTotalApiKey, ...], apps_per_key: int
    ) -> Generator[ScannedFile, None, None]:
        assert apps_to_scan == apps
        assert len(credentials) == api_key_count
        assert apps_per_key == 2
        yield ScannedFile(index=1, path=apps[1][0], version=apps[1][1], summary=summarize_scan_results(beta_results), results=beta_results)
        yield ScannedFile(index=0, path=apps[0][0], version=apps[0][1], summary=summarize_scan_results(alpha_results), results=alpha_results)

    def upload_dummy_app(path: Path) -> str:
        uploaded.append(path)
        return f"""https://example.invalid/{path.name}"""

    monkeypatch.setattr(check_installations, "read_virus_total_api_keys", read_dummy_keys)
    monkeypatch.setattr(check_installations, "scan_files_with_vt", completed_scans)
    monkeypatch.setattr(check_installations, "upload_app", upload_dummy_app)
    monkeypatch.setattr(check_installations, "console", Console(file=output, width=120))

    records = check_installations.scan_apps_with_vt(apps, apps_per_key=2)

    assert uploaded == [Path("beta"), Path("alpha")]
    assert [record["app_data"]["app_name"] for record in records] == ["alpha", "beta"]
    assert [record["app_data"]["version"] for record in records] == ["1", "2"]
    assert [record["app_data"]["positive_pct"] for record in records] == [0.0, 100.0]
    assert [record["app_data"]["app_url"] for record in records] == ["https://example.invalid/alpha", "https://example.invalid/beta"]
    assert [record["engine_results"][0]["engine_name"] for record in records] == ["alpha-engine", "beta-engine"]
    displayed = output.getvalue()
    assert re.search(rf"""API keys available\s+{api_key_count}""", displayed)
    assert re.search(rf"""API keys in use\s+{min(api_key_count, len(apps))}""", displayed)
    assert re.search(r"Apps per key \(configured\)\s+2", displayed)
    assert re.search(r"Concurrent scans \(maximum\)\s+2", displayed)
    assert re.search(r"Requests per key\s+1 at a time", displayed)
    assert all(credential.api_key not in displayed and credential.account_name not in displayed for credential in credentials)


def test_empty_scan_never_reads_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_read() -> tuple[VirusTotalApiKey, ...]:
        raise AssertionError("An empty scan must not load credentials.")

    monkeypatch.setattr(check_installations, "read_virus_total_api_keys", forbidden_read)

    assert check_installations.scan_apps_with_vt([], apps_per_key=1) == []


def test_invalid_credentials_fail_the_scan(monkeypatch: pytest.MonkeyPatch) -> None:
    def invalid_credentials() -> tuple[VirusTotalApiKey, ...]:
        raise ValueError("Invalid dummy credentials.")

    monkeypatch.setattr(check_installations, "read_virus_total_api_keys", invalid_credentials)

    with pytest.raises(ValueError, match="Invalid dummy credentials"):
        check_installations.scan_apps_with_vt([(Path("alpha"), None)], apps_per_key=1)
