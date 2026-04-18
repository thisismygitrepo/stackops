from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import stackops.utils.accessories as accessories
import stackops.utils.code as code_utils
import stackops.utils.meta as meta_utils
from stackops.scripts.python.helpers.helpers_croshell import croshell_impl


@dataclass(frozen=True, slots=True)
class LaunchInvocation:
    script: str
    strict: bool


def test_build_preprogram_contains_bootstrap_and_fallback_message() -> None:
    preprogram = croshell_impl._build_preprogram()

    assert 'print_logo("StackOps")' in preprogram
    assert "Croshell: stackops is not installed in the current environment." in preprogram


def test_build_fire_line_for_json_visidata_avoids_pyarrow() -> None:
    command = croshell_impl._build_fire_line(
        file_obj=Path("report.json"),
        pyfile=Path("/tmp/script.py"),
        nb_target=Path("/tmp/script.ipynb"),
        backend="visidata",
        interactivity="-i",
        ipython_profile="default",
        uv_python_line="--python 3.14",
        uv_project_line="--project /tmp/project",
        user_uv_with_line="--with rich",
        uv_with=None,
    )

    assert '--with visidata vd "report.json"' in command
    assert "pyarrow" not in command


def test_croshell_jupyter_backend_writes_script_and_notebook(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tmp_home = tmp_path.joinpath("home")
    tmp_home.mkdir()
    tmp_home.joinpath("code/stackops").mkdir(parents=True)
    cwd = tmp_path.joinpath("cwd")
    cwd.mkdir()
    launches: list[LaunchInvocation] = []

    def fake_home(_cls: type[Path]) -> Path:
        return tmp_home

    def fake_cwd(_cls: type[Path]) -> Path:
        return cwd

    def fake_lambda_to_python_script(
        function: object,
        in_global: bool,
        import_module: bool,
    ) -> str:
        _ = function, in_global, import_module
        return "# inspect-script\n"

    def fake_randstr() -> str:
        return "fixed-id"

    def fake_exit_then_run_shell_script(script: str, strict: bool) -> None:
        launches.append(LaunchInvocation(script=script, strict=strict))

    monkeypatch.setattr(croshell_impl.Path, "home", classmethod(fake_home))
    monkeypatch.setattr(croshell_impl.Path, "cwd", classmethod(fake_cwd))
    monkeypatch.setattr(meta_utils, "lambda_to_python_script", fake_lambda_to_python_script)
    monkeypatch.setattr(accessories, "randstr", fake_randstr)
    monkeypatch.setattr(code_utils, "exit_then_run_shell_script", fake_exit_then_run_shell_script)

    croshell_impl.croshell(
        path=None,
        project_path=str(tmp_path.joinpath("project")),
        uv_with=None,
        backend="jupyter",
        profile=None,
        frozen=False,
    )

    script_path = tmp_home.joinpath("tmp_results/tmp_scripts/python/croshell/fixed-id/script.py")
    notebook_path = script_path.with_suffix(".ipynb")

    assert script_path.exists()
    assert notebook_path.exists()
    assert "# inspect-script" in script_path.read_text(encoding="utf-8")
    assert launches == [
        LaunchInvocation(
            script=f"uv run   --project {tmp_path.joinpath('project')} --with jupyterlab  jupyter-lab {notebook_path}",
            strict=False,
        )
    ]
