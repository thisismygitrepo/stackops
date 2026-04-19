

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import cast

from click import Command, Context
from click.exceptions import Exit
import pytest
import requests
import typer

import stackops
import stackops.utils.code as code_utils
import stackops.utils.options as options_utils
import stackops.utils.source_of_truth as source_of_truth
from stackops.scripts.python.helpers.helpers_devops import run_script as run_script_module
from stackops.scripts.python.helpers.helpers_search import script_help


@dataclass(frozen=True, slots=True)
class FakeResponse:
    status_code: int
    text: str


def _context() -> typer.Context:
    return cast(typer.Context, Context(Command("run-script")))


def test_run_py_script_requires_name_or_interactive(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(Exit) as exc_info:
        run_script_module.run_py_script(
            ctx=_context(),
            name="",
            where="all",
            interactive=False,
            command=False,
            list_scripts=False,
        )

    assert exc_info.value.exit_code == 1
    assert "You must provide a script name" in capsys.readouterr().out


def test_run_py_script_lists_scripts_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    called_with: list[str] = []

    def fake_list_available_scripts(where: str) -> None:
        called_with.append(where)

    monkeypatch.setattr(script_help, "list_available_scripts", fake_list_available_scripts)

    run_script_module.run_py_script(
        ctx=_context(),
        name="",
        where="custom",
        interactive=False,
        command=False,
        list_scripts=True,
    )

    assert called_with == ["custom"]


def test_run_py_script_executes_explicit_python_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path.joinpath("demo.py")
    script_path.write_text("""print("demo")\n""", encoding="utf-8")
    calls: list[tuple[list[str], str | None, bool]] = []

    def fake_run(args: list[str], cwd: str | None, check: bool) -> subprocess.CompletedProcess[str]:
        calls.append((args, cwd, check))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_script_module.run_py_script(
        ctx=_context(),
        name=str(script_path),
        where="all",
        interactive=False,
        command=False,
        list_scripts=False,
    )

    assert calls == [([sys.executable, str(script_path)], str(stackops.__path__[0]), True)]


def test_run_py_script_filters_unwanted_matches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    private_root = tmp_path.joinpath("private")
    public_root = tmp_path.joinpath("public")
    library_root = tmp_path.joinpath("library")
    defaults_path = tmp_path.joinpath("defaults.ini")
    for root in (private_root, public_root, library_root):
        root.mkdir()

    valid_python = private_root.joinpath("nested", "matrix.py")
    valid_python.parent.mkdir(parents=True)
    valid_python.write_text("""print(\"ok\")\n""", encoding="utf-8")

    valid_shell = public_root.joinpath("tools", "matrix.sh")
    valid_shell.parent.mkdir(parents=True)
    valid_shell.write_text("""echo ok\n""", encoding="utf-8")

    invalid_pyc = private_root.joinpath("__pycache__", "matrix.cpython-314.pyc")
    invalid_pyc.parent.mkdir(parents=True)
    invalid_pyc.write_text("", encoding="utf-8")

    invalid_checkpoint = private_root.joinpath(".ipynb_checkpoints", "matrix-checkpoint.py")
    invalid_checkpoint.parent.mkdir(parents=True)
    invalid_checkpoint.write_text("""print(\"stale\")\n""", encoding="utf-8")

    invalid_powershell = library_root.joinpath("powershell", "matrix.ps1")
    invalid_powershell.parent.mkdir(parents=True)
    invalid_powershell.write_text("""Write-Output ok\n""", encoding="utf-8")

    invalid_cmd = library_root.joinpath("windows", "matrix.cmd")
    invalid_cmd.parent.mkdir(parents=True)
    invalid_cmd.write_text("""echo ok\n""", encoding="utf-8")

    observed_options: list[list[str]] = []
    observed_shell_scripts: list[str] = []

    def fake_choose_from_options(options: list[str], multi: bool, msg: str, tv: bool, preview: str) -> str:
        observed_options.append(options)
        assert multi is False
        assert msg == "Select the script to run:"
        assert tv is True
        assert preview == "bat"
        return str(valid_python)

    def fake_get_uv_command_executing_python_file(
        python_file: str,
        uv_project_dir: str | None,
        uv_with: str | None,
        prepend_print: bool,
    ) -> str:
        assert python_file == str(valid_python)
        assert uv_project_dir is None
        assert uv_with is None
        assert prepend_print is False
        return "uv run chosen.py"

    def fake_exit_then_run_shell_script(script: str, strict: bool | None = None) -> None:
        observed_shell_scripts.append(script)
        assert strict is None

    monkeypatch.setattr(run_script_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(source_of_truth, "DEFAULTS_PATH", defaults_path)
    monkeypatch.setattr(source_of_truth, "SCRIPTS_ROOT_PRIVATE", private_root)
    monkeypatch.setattr(source_of_truth, "SCRIPTS_ROOT_PUBLIC", public_root)
    monkeypatch.setattr(source_of_truth, "SCRIPTS_ROOT_LIBRARY", library_root)
    monkeypatch.setattr(options_utils, "choose_from_options", fake_choose_from_options)
    monkeypatch.setattr(code_utils, "get_uv_command_executing_python_file", fake_get_uv_command_executing_python_file)
    monkeypatch.setattr(code_utils, "exit_then_run_shell_script", fake_exit_then_run_shell_script)

    run_script_module.run_py_script(
        ctx=_context(),
        name="matrix",
        where="all",
        interactive=False,
        command=False,
        list_scripts=False,
    )

    assert observed_options == [[str(valid_python), str(valid_shell)]]
    assert observed_shell_scripts == ["uv run chosen.py"]

    output = capsys.readouterr().out
    assert "__pycache__" not in output
    assert ".ipynb_checkpoints" not in output
    assert ".ps1" not in output
    assert ".cmd" not in output


def test_copy_script_to_local_fetches_script_and_uses_alias(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    requested_urls: list[str] = []

    def fake_get(url: str, timeout: int) -> FakeResponse:
        requested_urls.append(url)
        assert timeout == 30
        return FakeResponse(status_code=200, text="""print("copied")\n""")

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(source_of_truth, "CONFIG_ROOT", tmp_path)
    tmp_path.joinpath("scripts_python").mkdir()

    run_script_module.copy_script_to_local(
        ctx=_context(),
        name="sample",
        alias="local_name",
    )

    copied_path = tmp_path.joinpath("scripts_python", "local_name.py")
    assert requested_urls == [
        "https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/scripts/python/helpers/tmp_py_scripts/sample.py"
    ]
    assert copied_path.read_text(encoding="utf-8") == """print("copied")\n"""
