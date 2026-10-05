from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from stackops.jobs.installer.checks import check_installations, security_cli
from stackops.jobs.installer.checks.scan_history import RunScope
from stackops.utils import code
from stackops.utils.meta import lambda_to_python_script


@dataclass(frozen=True)
class ScanCall:
    targets: list[tuple[Path, str | None]]
    scope: RunScope
    requested: list[str]
    record: bool
    upload: bool
    concurrency: int | None
    records_root: Path


def _execute_serialized_worker(
    worker: Callable[[], object], uv_with: list[str] | None, uv_project_dir: str | None
) -> subprocess.CompletedProcess[bytes]:
    assert uv_with == ["vt-py"]
    assert uv_project_dir is None
    worker_source = lambda_to_python_script(worker, in_global=True, import_module=False)
    exec(worker_source, {})
    return subprocess.CompletedProcess[bytes](args=["serialized-worker"], returncode=0, stdout=b"", stderr=b"")


@pytest.fixture
def scan_calls(monkeypatch: pytest.MonkeyPatch) -> list[ScanCall]:
    calls: list[ScanCall] = []

    def capture_scan(
        apps_to_scan: list[tuple[Path, str | None]],
        scope: RunScope,
        requested: list[str],
        record: bool,
        upload: bool,
        concurrency: int | None,
        records_root: Path,
    ) -> None:
        calls.append(ScanCall(apps_to_scan, scope, requested, record, upload, concurrency, records_root))

    def collect_apps(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
        return [(Path(f"""/dummy/{name}"""), None) for name in app_names or ["all"]]

    monkeypatch.setitem(sys.modules, "stackops.jobs.installer.checks.scan_execution", SimpleNamespace(execute_scan=capture_scan))
    monkeypatch.setattr(check_installations, "collect_apps_to_scan", collect_apps)
    monkeypatch.setattr(code, "run_lambda_function", _execute_serialized_worker)
    return calls


@pytest.mark.parametrize(("record_arguments", "expected_record"), [([], True), (["--no-record"], False), (["-n"], False)])
def test_scan_serializes_recording_opt_out(
    record_arguments: list[str], expected_record: bool, tmp_path: Path, scan_calls: list[ScanCall]
) -> None:
    result = CliRunner().invoke(
        security_cli.get_app(),
        ["scan", "alpha, beta", "-c", "3", "-d", str(tmp_path), *record_arguments],
    )

    assert result.exit_code == 0, result.output
    assert scan_calls == [ScanCall([(Path("/dummy/alpha"), None), (Path("/dummy/beta"), None)], "apps", ["alpha", "beta"], expected_record, False, 3, tmp_path)]


def test_scan_serializes_path_as_a_runtime_independent_value(tmp_path: Path, scan_calls: list[ScanCall]) -> None:
    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"sample")

    result = CliRunner().invoke(
        security_cli.get_app(), ["scan", "-p", str(sample_path), "-n", "-c", "4", "-d", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert scan_calls == [ScanCall([(sample_path, None)], "path", [str(sample_path)], False, False, 4, tmp_path)]


def test_scan_all_short_option_selects_installed_apps(tmp_path: Path, scan_calls: list[ScanCall]) -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["scan", "-a", "-d", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert scan_calls == [ScanCall([(Path("/dummy/all"), None)], "all", [], True, False, None, tmp_path)]


@pytest.mark.parametrize("upload_option", ["--upload", "-u"])
@pytest.mark.parametrize("scope", ["apps", "all", "path"])
@pytest.mark.parametrize("record", [True, False])
def test_scan_serializes_upload_opt_in(
    upload_option: str, scope: RunScope, record: bool, tmp_path: Path, scan_calls: list[ScanCall]
) -> None:
    sample_path = tmp_path / "sample.bin"
    sample_path.write_bytes(b"sample")
    target_arguments = {"apps": ["alpha"], "all": ["--all"], "path": ["--path", str(sample_path)]}
    result = CliRunner().invoke(
        security_cli.get_app(),
        ["scan", *target_arguments[scope], upload_option, "--records-dir", str(tmp_path), *([] if record else ["--no-record"])],
    )

    assert result.exit_code == 0, result.output
    assert len(scan_calls) == 1
    assert (scan_calls[0].scope, scan_calls[0].record, scan_calls[0].upload) == (scope, record, True)


def test_scan_propagates_serialized_worker_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_worker(_worker: Callable[[], object], uv_with: list[str] | None, uv_project_dir: str | None) -> subprocess.CompletedProcess[bytes]:
        assert uv_with == ["vt-py"]
        assert uv_project_dir is None
        return subprocess.CompletedProcess[bytes](args=["serialized-worker"], returncode=17, stdout=b"", stderr=b"")

    monkeypatch.setattr(code, "run_lambda_function", fail_worker)
    with pytest.raises(typer.Exit) as raised_exit:
        security_cli.scan(apps="alpha", path=None, all_apps=False, no_record=False, upload=False, concurrency=1, records_dir=tmp_path)

    assert raised_exit.value.exit_code == 17


def test_scan_worker_turns_scan_failure_into_process_exit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_scan(
        apps_to_scan: list[tuple[Path, str | None]], scope: RunScope, requested: list[str],
        record: bool, upload: bool, concurrency: int | None, records_root: Path,
    ) -> None:
        assert apps_to_scan == [(tmp_path / "sample.bin", None)]
        assert (scope, requested, record, upload, concurrency, records_root) == ("path", [str(tmp_path / "sample.bin")], True, True, 1, tmp_path)
        raise typer.Exit(code=1)

    monkeypatch.setitem(sys.modules, "stackops.jobs.installer.checks.scan_execution", SimpleNamespace(execute_scan=fail_scan))
    with pytest.raises(SystemExit) as raised_exit:
        security_cli._run_scan(app_names=None, path_value=str(tmp_path / "sample.bin"), record=True, upload=True, concurrency=1, records_dir=str(tmp_path))

    assert raised_exit.value.code == 1


def test_list_apps_does_not_require_optional_scan_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    def collect_apps(app_names: list[str] | None) -> list[tuple[Path, str | None]]:
        assert app_names == ["rg"]
        return [(Path("/dummy/rg"), "dummy-version")]

    monkeypatch.setitem(sys.modules, "vt", None)
    monkeypatch.setitem(sys.modules, "aiohttp", None)
    monkeypatch.setattr(check_installations, "collect_apps_to_scan", collect_apps)
    result = CliRunner().invoke(security_cli.get_app(), ["list", "rg"])

    assert result.exit_code == 0, result.output
    assert "dummy-version" in result.output
    assert "/dummy/rg" in result.output


@pytest.mark.parametrize("concurrency", [0, -1])
def test_scan_rejects_invalid_concurrency_directly(concurrency: int, tmp_path: Path) -> None:
    with pytest.raises(typer.BadParameter, match="Must be at least 1"):
        security_cli.scan(apps="alpha", path=None, all_apps=False, no_record=False, upload=False, concurrency=concurrency, records_dir=tmp_path)


@pytest.mark.parametrize("concurrency", ["0", "-1", "invalid"])
def test_scan_cli_rejects_invalid_concurrency(concurrency: str) -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["scan", "alpha", "--concurrency", concurrency])

    assert result.exit_code == 2
    assert "--concurrency" in result.output


def test_scan_help_exposes_recording_opt_out_and_upload_opt_in() -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["scan", "--help"])
    help_text = " ".join(result.output.split())

    assert result.exit_code == 0, result.output
    assert "--no-record" in help_text
    assert "--record " not in help_text
    assert "--upload" in help_text
    assert "-u" in help_text
    assert "--concurrency" in help_text
    assert "configured account count" in help_text


@pytest.mark.parametrize("alias", ["s", "l", "u", "d", "i", "r", "h", "e"])
def test_security_command_aliases_expose_help_without_side_effects(alias: str) -> None:
    result = CliRunner().invoke(security_cli.get_app(), [alias, "--help"])

    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output


def test_security_help_documents_history_and_export_aliases() -> None:
    result = CliRunner().invoke(security_cli.get_app(), ["--help"])

    assert result.exit_code == 0, result.output
    assert "<h>" in result.output
    assert "<e>" in result.output
