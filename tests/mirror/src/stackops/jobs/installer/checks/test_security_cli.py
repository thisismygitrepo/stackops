from collections.abc import Callable
import importlib
from pathlib import Path
import subprocess
import sys

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


def test_scan_serializes_installed_app_names_record_setting_and_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    scan_calls: list[tuple[list[str] | None, bool, int | None]] = []

    def capture_scan(app_names: list[str] | None, write_reports_to_repo: bool, concurrency: int | None) -> list[AppData]:
        scan_calls.append((app_names, write_reports_to_repo, concurrency))
        return []

    monkeypatch.setattr(check_installations, "scan_installed_apps", capture_scan)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)

    security_cli.scan(apps="alpha, beta", path=None, record=True, concurrency=3)

    assert scan_calls == [(["alpha", "beta"], True, 3)]


def test_scan_serializes_path_as_a_runtime_independent_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_calls: list[tuple[Path, bool, int | None]] = []
    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"sample")

    def capture_scan(path: Path, record: bool, concurrency: int | None) -> None:
        scan_calls.append((path, record, concurrency))

    monkeypatch.setattr(security_helper, "scan_single_path", capture_scan)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)

    security_cli.scan(apps=None, path=sample_path, record=None, concurrency=4)

    assert scan_calls == [(sample_path, False, 4)]


def test_scan_propagates_serialized_worker_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_worker(_worker: Callable[[], object], uv_with: list[str] | None, uv_project_dir: str | None) -> subprocess.CompletedProcess[bytes]:
        assert uv_with == ["vt-py"]
        assert uv_project_dir is None
        return subprocess.CompletedProcess[bytes](args=["serialized-worker"], returncode=17, stdout=b"", stderr=b"")

    monkeypatch.setattr(code, "run_lambda_function", fail_worker)

    with pytest.raises(typer.Exit) as raised_exit:
        security_cli.scan(apps="alpha", path=None, record=True, concurrency=1)

    assert raised_exit.value.exit_code == 17


def test_scan_worker_turns_scan_failure_into_process_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_scan(app_names: list[str] | None, write_reports_to_repo: bool, concurrency: int | None) -> list[AppData]:
        assert app_names == ["alpha"]
        assert write_reports_to_repo is True
        assert concurrency == 1
        raise typer.Exit(code=1)

    monkeypatch.setattr(check_installations, "scan_installed_apps", fail_scan)
    with pytest.raises(SystemExit) as raised_exit:
        security_cli._run_scan(app_names=["alpha"], path_value=None, record=True, concurrency=1)

    assert raised_exit.value.code == 1


def test_list_apps_does_not_require_optional_scan_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    from stackops.jobs.installer.checks import vt_scanner

    def collect_apps(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
        assert app_names == ["rg"]
        return [(Path("/dummy/rg"), "dummy-version")]

    monkeypatch.setitem(sys.modules, "vt", None)
    monkeypatch.setitem(sys.modules, "aiohttp", None)
    importlib.reload(vt_scanner)
    monkeypatch.setattr(check_installations, "collect_apps_to_scan", collect_apps)
    result = CliRunner().invoke(security_cli.get_app(), ["list", "rg"])

    assert result.exit_code == 0
    assert "dummy-version" in result.output
    assert "/dummy/rg" in result.output


@pytest.mark.parametrize("concurrency", [0, -1])
def test_scan_rejects_invalid_concurrency_directly(concurrency: int) -> None:
    with pytest.raises(typer.BadParameter, match="Must be at least 1"):
        security_cli.scan(apps="alpha", path=None, record=True, concurrency=concurrency)


@pytest.mark.parametrize("concurrency", ["0", "-1", "invalid"])
def test_scan_cli_rejects_invalid_concurrency(concurrency: str) -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["scan", "alpha", "--concurrency", concurrency])

    assert result.exit_code == 2
    assert "--concurrency" in result.output


@pytest.mark.parametrize("concurrency", [None, "3"])
def test_scan_cli_passes_default_or_configured_concurrency(concurrency: str | None, monkeypatch: pytest.MonkeyPatch) -> None:
    scan_calls: list[tuple[list[str] | None, bool, int | None]] = []

    def capture_scan(app_names: list[str] | None, write_reports_to_repo: bool, concurrency: int | None) -> list[AppData]:
        scan_calls.append((app_names, write_reports_to_repo, concurrency))
        return []

    monkeypatch.setattr(check_installations, "scan_installed_apps", capture_scan)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)
    arguments = ["scan", "alpha"]
    if concurrency is not None:
        arguments.extend(["--concurrency", concurrency])

    result = CliRunner().invoke(security_cli.get_app(), arguments)

    assert result.exit_code == 0
    assert scan_calls == [(["alpha"], True, None if concurrency is None else int(concurrency))]


def test_scan_help_explains_concurrency() -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["scan", "--help"])
    help_text = " ".join(result.output.split())

    assert result.exit_code == 0
    assert "--concurrency" in help_text
    assert "configured accounts" in help_text
    assert "--apps-per-key" not in help_text
