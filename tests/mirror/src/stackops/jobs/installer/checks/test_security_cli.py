from collections.abc import Callable
from pathlib import Path
import subprocess

import pytest
import typer

from stackops.jobs.installer.checks import check_installations, security_cli, security_helper
from stackops.jobs.installer.checks.report_utils import AppData
from stackops.utils import code
from stackops.utils.meta import lambda_to_python_script


def _execute_serialized_worker(
    worker: Callable[[], object],
    uv_with: list[str] | None,
    uv_project_dir: str | None,
) -> subprocess.CompletedProcess[bytes]:
    assert uv_with == ["vt-py"]
    assert uv_project_dir is None
    worker_source = lambda_to_python_script(worker, in_global=True, import_module=False)
    exec(worker_source, {})
    return subprocess.CompletedProcess[bytes](args=["serialized-worker"], returncode=0, stdout=b"", stderr=b"")


def test_scan_serializes_installed_app_names_and_record_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    scan_calls: list[tuple[list[str] | None, bool]] = []

    def capture_scan(app_names: list[str] | None, write_reports_to_repo: bool) -> list[AppData]:
        scan_calls.append((app_names, write_reports_to_repo))
        return []

    monkeypatch.setattr(check_installations, "scan_installed_apps", capture_scan)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)

    security_cli.scan(apps="alpha, beta", path=None, record=True)

    assert scan_calls == [(["alpha", "beta"], True)]


def test_scan_serializes_path_as_a_runtime_independent_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_calls: list[tuple[Path, bool]] = []
    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"sample")

    def capture_scan(path: Path, record: bool) -> None:
        scan_calls.append((path, record))

    monkeypatch.setattr(security_helper, "scan_single_path", capture_scan)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)

    security_cli.scan(apps=None, path=sample_path, record=None)

    assert scan_calls == [(sample_path, False)]


def test_scan_propagates_serialized_worker_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_worker(
        _worker: Callable[[], object],
        uv_with: list[str] | None,
        uv_project_dir: str | None,
    ) -> subprocess.CompletedProcess[bytes]:
        assert uv_with == ["vt-py"]
        assert uv_project_dir is None
        return subprocess.CompletedProcess[bytes](args=["serialized-worker"], returncode=17, stdout=b"", stderr=b"")

    monkeypatch.setattr(code, "run_lambda_function", fail_worker)

    with pytest.raises(typer.Exit) as raised_exit:
        security_cli.scan(apps="alpha", path=None, record=True)

    assert raised_exit.value.exit_code == 17
