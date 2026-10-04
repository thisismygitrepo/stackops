from collections.abc import Callable
from pathlib import Path
import subprocess

import pytest
import typer
from typer.testing import CliRunner

from stackops.jobs.installer.checks import check_installations, security_cli, security_helper
from stackops.jobs.installer.checks.report_utils import AppData
from stackops.utils import code
from stackops.utils.meta import lambda_to_python_script


def _execute_serialized_worker(
    worker: Callable[[], object], uv_with: list[str] | None, uv_project_dir: str | None
) -> subprocess.CompletedProcess[bytes]:
    assert uv_with == ["vt-py"]
    assert uv_project_dir is None
    worker_source = lambda_to_python_script(worker, in_global=True, import_module=False)
    exec(worker_source, {})
    return subprocess.CompletedProcess[bytes](args=["serialized-worker"], returncode=0, stdout=b"", stderr=b"")


def test_scan_serializes_installed_app_names_record_setting_and_apps_per_key(monkeypatch: pytest.MonkeyPatch) -> None:
    scan_calls: list[tuple[list[str] | None, bool, int]] = []

    def capture_scan(app_names: list[str] | None, write_reports_to_repo: bool, apps_per_key: int) -> list[AppData]:
        scan_calls.append((app_names, write_reports_to_repo, apps_per_key))
        return []

    monkeypatch.setattr(check_installations, "scan_installed_apps", capture_scan)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)

    security_cli.scan(apps="alpha, beta", path=None, record=True, apps_per_key=3)

    assert scan_calls == [(["alpha", "beta"], True, 3)]


def test_scan_serializes_path_as_a_runtime_independent_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_calls: list[tuple[Path, bool, int]] = []
    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"sample")

    def capture_scan(path: Path, record: bool, apps_per_key: int) -> None:
        scan_calls.append((path, record, apps_per_key))

    monkeypatch.setattr(security_helper, "scan_single_path", capture_scan)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)

    security_cli.scan(apps=None, path=sample_path, record=None, apps_per_key=4)

    assert scan_calls == [(sample_path, False, 4)]


def test_scan_propagates_serialized_worker_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_worker(_worker: Callable[[], object], uv_with: list[str] | None, uv_project_dir: str | None) -> subprocess.CompletedProcess[bytes]:
        assert uv_with == ["vt-py"]
        assert uv_project_dir is None
        return subprocess.CompletedProcess[bytes](args=["serialized-worker"], returncode=17, stdout=b"", stderr=b"")

    monkeypatch.setattr(code, "run_lambda_function", fail_worker)

    with pytest.raises(typer.Exit) as raised_exit:
        security_cli.scan(apps="alpha", path=None, record=True, apps_per_key=1)

    assert raised_exit.value.exit_code == 17


@pytest.mark.parametrize("apps_per_key", [0, -1])
def test_scan_rejects_invalid_apps_per_key_directly(apps_per_key: int) -> None:
    with pytest.raises(typer.BadParameter, match="Must be at least 1"):
        security_cli.scan(apps="alpha", path=None, record=True, apps_per_key=apps_per_key)


@pytest.mark.parametrize("apps_per_key", ["0", "-1", "invalid"])
def test_scan_cli_rejects_invalid_apps_per_key(apps_per_key: str) -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["scan", "alpha", "--apps-per-key", apps_per_key])

    assert result.exit_code == 2
    assert "--apps-per-key" in result.output


@pytest.mark.parametrize("apps_per_key", [None, "3"])
def test_scan_cli_passes_default_or_configured_apps_per_key(apps_per_key: str | None, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_calls: list[tuple[list[str] | None, bool, int]] = []

    def capture_scan(app_names: list[str] | None, write_reports_to_repo: bool, apps_per_key: int) -> list[AppData]:
        scan_calls.append((app_names, write_reports_to_repo, apps_per_key))
        return []

    monkeypatch.setattr(check_installations, "scan_installed_apps", capture_scan)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)
    arguments = ["scan", "alpha"]
    if apps_per_key is not None:
        arguments.extend(["--apps-per-key", apps_per_key])

    result = CliRunner().invoke(security_cli.get_app(), arguments)

    assert result.exit_code == 0
    assert scan_calls == [(["alpha"], True, 1 if apps_per_key is None else int(apps_per_key))]


def test_scan_help_explains_apps_per_key() -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["scan", "--help"])
    help_text = " ".join(result.output.split())

    assert result.exit_code == 0
    assert "--apps-per-key" in help_text
    assert "default: 1" in help_text
    assert "key count x apps per key" in help_text
