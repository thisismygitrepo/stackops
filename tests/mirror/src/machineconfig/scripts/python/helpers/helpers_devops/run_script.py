from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

from click import Command, Context
from click.exceptions import Exit
import pytest
import requests

import machineconfig
import machineconfig.utils.source_of_truth as source_of_truth
from machineconfig.scripts.python.helpers.helpers_devops import run_script as run_script_module
from machineconfig.scripts.python.helpers.helpers_search import script_help


@dataclass(frozen=True, slots=True)
class FakeResponse:
    status_code: int
    text: str


def _context() -> Context:
    return Context(Command("run-script"))


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

    assert calls == [([sys.executable, str(script_path)], str(machineconfig.__path__[0]), True)]


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
        "https://raw.githubusercontent.com/thisismygitrepo/machineconfig/refs/heads/main/src/machineconfig/scripts/python/helpers/tmp_py_scripts/sample.py"
    ]
    assert copied_path.read_text(encoding="utf-8") == """print("copied")\n"""
