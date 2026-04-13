from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python.helpers.helpers_utils import pyproject_utils_app as module


def _install_module(monkeypatch: pytest.MonkeyPatch, module_name: str, attrs: dict[str, object]) -> None:
    fake_module = ModuleType(module_name)
    for attr_name, attr_value in attrs.items():
        setattr(fake_module, attr_name, attr_value)
    monkeypatch.setitem(sys.modules, module_name, fake_module)


def test_type_hint_rejects_missing_path(capsys: pytest.CaptureFixture[str]) -> None:
    missing_path = Path("/tmp/machineconfig-pyproject-utils-app-missing")

    with pytest.raises(module.typer.Exit) as excinfo:
        module.type_hint(path=str(missing_path), dependency="self-contained")

    captured = capsys.readouterr()
    assert excinfo.value.exit_code == 1
    assert "does not exist" in captured.err


def test_type_hint_scans_project_root_and_skips_venv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    project_root = tmp_path
    project_root.joinpath("pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    source_dtypes = project_root.joinpath("pkg", "dtypes.py")
    source_dtypes.parent.mkdir(parents=True)
    source_dtypes.write_text("VALUE = 1\n", encoding="utf-8")
    venv_dtypes = project_root.joinpath(".venv", "pkg", "dtypes.py")
    venv_dtypes.parent.mkdir(parents=True)
    venv_dtypes.write_text("VALUE = 2\n", encoding="utf-8")

    module.type_hint(path=str(project_root), dependency="import")

    captured = capsys.readouterr()
    assert str(source_dtypes.resolve()) in captured.out
    assert str(source_dtypes.with_name("dtypes_names.py").resolve()) in captured.out
    assert str(venv_dtypes.resolve()) not in captured.out


def test_upgrade_packages_resolves_paths_and_forwards_clean_groups(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: dict[str, object] = {}

    def fake_clean_dependency_groups(project_root: Path, group_names: list[str]) -> None:
        calls["clean"] = (project_root, group_names.copy())

    def fake_generate_uv_add_commands(pyproject_path: Path, output_path: Path) -> None:
        calls["generate"] = (pyproject_path, output_path)

    _install_module(
        monkeypatch,
        "machineconfig.utils.upgrade_packages",
        {"clean_dependency_groups": fake_clean_dependency_groups, "generate_uv_add_commands": fake_generate_uv_add_commands},
    )

    module.upgrade_packages(root=str(tmp_path), clean_group=["dev", "plot"])

    root_resolved = tmp_path.resolve()
    assert calls["clean"] == (root_resolved, ["dev", "plot"])
    assert calls["generate"] == (root_resolved.joinpath("pyproject.toml"), root_resolved.joinpath("pyproject_init.sh"))


def test_init_project_delegates_to_helper_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_init_project(*, name: str | None, tmp_dir: bool, python: str, libraries: str | None, group: str | None) -> None:
        calls.append({"name": name, "tmp_dir": tmp_dir, "python": python, "libraries": libraries, "group": group})

    _install_module(monkeypatch, "machineconfig.scripts.python.helpers.helpers_utils.python", {"init_project": fake_init_project})

    module.init_project(name="demo", tmp_dir=True, python="3.14", libraries="rich textual", group="l")

    assert calls == [{"name": "demo", "tmp_dir": True, "python": "3.14", "libraries": "rich textual", "group": "l"}]


def test_type_check_resolves_repo_root_and_runs_lint_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    nested_dir = repo_root.joinpath("pkg", "nested")
    nested_dir.mkdir(parents=True)
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    script_path = repo_root.joinpath("lint_and_type_check.py")
    script_path.write_text("print('ok')\n", encoding="utf-8")
    calls: dict[str, object] = {}

    def fake_get_path_reference_path(module_obj: ModuleType, path_reference: str) -> Path:
        calls["path_reference"] = (module_obj, path_reference)
        return script_path

    def fake_run(command: list[str], cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        calls["run"] = {"command": command.copy(), "cwd": cwd, "check": check}
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(module, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.type_check(repo=str(nested_dir))

    assert calls["path_reference"] == (
        module.ai_scripts,
        module.ai_scripts.LINT_AND_TYPE_CHECK_PATH_REFERENCE,
    )
    assert calls["run"] == {
        "command": ["uv", "run", str(script_path)],
        "cwd": repo_root.resolve(),
        "check": False,
    }


def test_type_check_rejects_path_without_pyproject(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_root = tmp_path.joinpath("no-pyproject")
    repo_root.mkdir()

    with pytest.raises(module.typer.Exit) as excinfo:
        module.type_check(repo=str(repo_root))

    captured = capsys.readouterr()
    assert excinfo.value.exit_code == 1
    assert "Could not find pyproject.toml" in captured.err


def test_type_check_propagates_subprocess_exit_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    script_path = repo_root.joinpath("lint_and_type_check.py")
    script_path.write_text("print('ok')\n", encoding="utf-8")

    def fake_get_path_reference_path(_module_obj: ModuleType, _path_reference: str) -> Path:
        return script_path

    def fake_run(command: list[str], cwd: Path, check: bool) -> subprocess.CompletedProcess[str]:
        assert command == ["uv", "run", str(script_path)]
        assert cwd == repo_root.resolve()
        assert check is False
        return subprocess.CompletedProcess(args=command, returncode=7)

    monkeypatch.setattr(module, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    with pytest.raises(module.typer.Exit) as excinfo:
        module.type_check(repo=str(repo_root))

    assert excinfo.value.exit_code == 7


def test_get_app_help_lists_core_commands() -> None:
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["--help"])

    assert result.exit_code == 0
    assert "init-project" in result.stdout
    assert "upgrade-packages" in result.stdout
    assert "type-hint" in result.stdout
    assert "type-check" in result.stdout
    assert "reference-test" in result.stdout


def test_reference_test_help_lists_verbose_flag() -> None:
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["reference-test", "--help"])

    assert result.exit_code == 0
    assert "--verbose" in result.stdout


def test_reference_test_reports_success_for_repo_with_valid_targets(tmp_path: Path) -> None:
    repo_root = tmp_path
    package_dir = repo_root.joinpath("src", "pkg")
    package_dir.mkdir(parents=True)
    package_dir.joinpath("asset.txt").write_text("ok\n", encoding="utf-8")
    package_dir.joinpath("__init__.py").write_text('ASSET_PATH_REFERENCE = "asset.txt"\n', encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["reference-test", str(repo_root)])

    assert result.exit_code == 0
    assert "✅ Reference Audit Passed" in result.output
    assert "Resolved Targets" in result.output


def test_reference_test_verbose_reports_rich_details_for_success(tmp_path: Path) -> None:
    repo_root = tmp_path
    package_dir = repo_root.joinpath("src", "pkg")
    package_dir.mkdir(parents=True)
    package_dir.joinpath("asset.txt").write_text("ok\n", encoding="utf-8")
    package_dir.joinpath("__init__.py").write_text('ASSET_PATH_REFERENCE = "asset.txt"\n', encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["reference-test", str(repo_root), "--verbose"])

    assert result.exit_code == 0
    assert "🧹 Excluded Directories" in result.output
    assert "✅ No invalid _PATH_REFERENCE definitions found." in result.output
    assert "✅ No missing _PATH_REFERENCE targets found." in result.output


def test_reference_test_reports_missing_targets(tmp_path: Path) -> None:
    repo_root = tmp_path
    package_dir = repo_root.joinpath("src", "pkg")
    package_dir.mkdir(parents=True)
    package_dir.joinpath("__init__.py").write_text('ASSET_PATH_REFERENCE = "missing.txt"\n', encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["reference-test", str(repo_root)])

    assert result.exit_code == 1
    assert "❌ Reference Audit Failed" in result.output
    assert "❌ Failure Details" in result.output
    assert "missing.txt" in result.output


def test_reference_test_verbose_reports_rich_details_for_failures(tmp_path: Path) -> None:
    repo_root = tmp_path
    package_dir = repo_root.joinpath("src", "pkg")
    package_dir.mkdir(parents=True)
    package_dir.joinpath("__init__.py").write_text('ASSET_PATH_REFERENCE = "missing.txt"\n', encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(module.get_app(), ["reference-test", str(repo_root), "--verbose"])

    assert result.exit_code == 1
    assert "❌ Missing Targets" in result.output
    assert "missing.txt" in result.output
