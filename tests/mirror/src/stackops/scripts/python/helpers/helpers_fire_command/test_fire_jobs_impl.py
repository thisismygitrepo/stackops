import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_fire_command import fire_jobs_impl
from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper import FireJobArgs


def write_job(directory: Path) -> Path:
    job = directory / "job.py"
    job.write_text(
        """from pathlib import Path


def bump(log: str) -> None:
    with Path(log).open("a", encoding="utf-8") as handle:
        handle.write("called\\n")
""",
        encoding="utf-8",
    )
    return job


def build_tokens(args: FireJobArgs, job: Path, kwargs_dict: dict[str, object]) -> list[str]:
    command = fire_jobs_impl._build_command(
        args=args, choice_file=job, choice_function="bump", kwargs_dict=kwargs_dict, repo_root=None, fire_args="--log=x", randstr_func=lambda length: "x" * length
    )
    return shlex.split(command)


@pytest.mark.skipif(os.name == "nt", reason="Parses the POSIX shell handoff.")
def test_function_route_declares_the_fire_package(tmp_path: Path) -> None:
    tokens = build_tokens(args=FireJobArgs(mode="run"), job=write_job(directory=tmp_path), kwargs_dict={})
    assert tokens[tokens.index("--with") + 1] == "fire"
    assert tokens[tokens.index("-m") + 1] == "fire"
    assert tokens.index("--with") < tokens.index("python")


@pytest.mark.skipif(os.name == "nt", reason="Parses the POSIX shell handoff.")
def test_module_route_does_not_use_the_fire_package(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    tokens = build_tokens(args=FireJobArgs(mode="run", module=True), job=write_job(directory=tmp_path), kwargs_dict={})
    assert "--with" not in tokens


@pytest.mark.skipif(os.name == "nt", reason="Executes the POSIX shell handoff.")
@pytest.mark.parametrize("repo_developer", [False, True])
def test_generated_script_runs_and_calls_the_function_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, repo_developer: bool) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(fire_jobs_impl, "IS_REPO_DEVELOPER", repo_developer)
    log = tmp_path / "calls.log"
    tokens = build_tokens(args=FireJobArgs(mode="run", script=True), job=write_job(directory=tmp_path), kwargs_dict={"log": str(log)})
    assert "fire" not in tokens
    assert "--with" not in tokens
    subprocess.run([sys.executable, tokens[-1]], cwd=tmp_path, capture_output=True, text=True, check=True)
    assert log.read_text(encoding="utf-8") == "called\n"
