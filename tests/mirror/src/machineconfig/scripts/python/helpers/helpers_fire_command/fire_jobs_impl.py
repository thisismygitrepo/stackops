from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

import machineconfig.utils.accessories as accessories
import machineconfig.utils.code as code_module
import machineconfig.utils.path_helper as path_helper
import machineconfig.utils.ve as ve_module
from machineconfig.scripts.python.helpers.helpers_fire_command import file_wrangler as file_wrangler_module
from machineconfig.scripts.python.helpers.helpers_fire_command import fire_jobs_impl
from machineconfig.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper import FireJobArgs


def test_get_search_root_uses_repo_root_when_requested(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    nested_path = repo_root.joinpath("nested")
    nested_path.mkdir(parents=True)

    monkeypatch.setattr(fire_jobs_impl.Path, "cwd", lambda: nested_path)
    monkeypatch.setattr(accessories, "get_repo_root", lambda path: repo_root)

    assert fire_jobs_impl._get_search_root(root_repo=False) is None
    assert fire_jobs_impl._get_search_root(root_repo=True) == repo_root

    monkeypatch.setattr(accessories, "get_repo_root", lambda path: None)
    with pytest.raises(ValueError, match="inside a git repository"):
        fire_jobs_impl._get_search_root(root_repo=True)


def test_handle_marimo_skips_conversion_for_valid_notebook(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    choice_file = tmp_path.joinpath("notebook.py")
    repo_root = tmp_path.joinpath("repo")
    choice_file.write_text("""print("ok")\n""", encoding="utf-8")
    repo_root.mkdir()
    commands: list[list[str]] = []
    launched_scripts: list[str] = []

    def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = (capture_output, text, check)
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="valid notebook", stderr="")

    def fake_exit_then_run_shell_script(script: str) -> None:
        launched_scripts.append(script)

    monkeypatch.setattr(fire_jobs_impl.subprocess, "run", fake_run)
    monkeypatch.setattr(code_module, "exit_then_run_shell_script", fake_exit_then_run_shell_script)

    fire_jobs_impl._handle_marimo(choice_file=choice_file, repo_root=repo_root, randstr_func=lambda _length: "unused")

    assert commands == [["uv", "run", "--project", str(repo_root), "--with", "marimo", "marimo", "check", str(choice_file)]]
    assert len(launched_scripts) == 1
    assert "marimo convert" not in launched_scripts[0]
    assert f"marimo edit --host 0.0.0.0 {choice_file}" in launched_scripts[0]


def test_handle_marimo_converts_non_notebook_before_launch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    choice_file = tmp_path.joinpath("report.py")
    choice_file.write_text("""print("report")\n""", encoding="utf-8")
    launched_scripts: list[str] = []

    def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = (command, capture_output, text, check)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="failed to parse")

    def fake_exit_then_run_shell_script(script: str) -> None:
        launched_scripts.append(script)

    monkeypatch.setattr(fire_jobs_impl.subprocess, "run", fake_run)
    monkeypatch.setattr(code_module, "exit_then_run_shell_script", fake_exit_then_run_shell_script)
    monkeypatch.setattr(fire_jobs_impl.Path, "home", lambda: tmp_path)

    fire_jobs_impl._handle_marimo(choice_file=choice_file, repo_root=None, randstr_func=lambda _length: "seed")

    tmp_dir = tmp_path.joinpath("tmp_results", "tmp_scripts", "marimo", "report_seed")
    assert tmp_dir.is_dir()
    assert len(launched_scripts) == 1
    assert f"cd {tmp_dir}" in launched_scripts[0]
    assert f"marimo convert {choice_file} -o marimo_nb.py" in launched_scripts[0]
    assert "marimo edit --host 0.0.0.0 marimo_nb.py" in launched_scripts[0]


def test_build_python_exe_line_includes_interactive_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    choice_file = tmp_path.joinpath("tool.py")
    repo_root = tmp_path.joinpath("repo")
    choice_file.write_text("""print("tool")\n""", encoding="utf-8")
    repo_root.mkdir()

    def fake_get_ve_path_and_ipython_profile(init_path: Path) -> tuple[str | None, str | None]:
        assert init_path == choice_file
        return (str(tmp_path.joinpath(".venv")), "analysis")

    monkeypatch.setattr(ve_module, "get_ve_path_and_ipython_profile", fake_get_ve_path_and_ipython_profile)

    command = fire_jobs_impl._build_python_exe_line(
        module=False, interactive=True, frozen=True, streamlit=False, environment="", jupyter=False, choice_file=choice_file, repo_root=repo_root
    )

    assert "uv run" in command
    assert "--frozen" in command
    assert f"--project {repo_root}" in command
    assert "ipython" in command
    assert "-i" in command
    assert "--profile analysis" in command


def test_build_final_command_and_apply_modifiers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    choice_file = tmp_path.joinpath("app.py")
    choice_file.write_text("""print("app")\n""", encoding="utf-8")
    repo_root = tmp_path

    fire_command = fire_jobs_impl._build_final_command(
        debug=False,
        module=False,
        streamlit=False,
        hold_directory=False,
        cmd=False,
        exe_line="uv run python",
        choice_file=choice_file,
        choice_file_adjusted=str(choice_file),
        choice_function="run",
        fire_args="--limit=2",
    )
    streamlit_command = fire_jobs_impl._build_final_command(
        debug=False,
        module=False,
        streamlit=True,
        hold_directory=False,
        cmd=False,
        exe_line="streamlit run",
        choice_file=choice_file,
        choice_file_adjusted=str(choice_file),
        choice_function=None,
        fire_args="",
    )

    monkeypatch.setattr(file_wrangler_module, "add_to_path", lambda path_variable, directory: f"export {path_variable}={directory}")

    modified_command = fire_jobs_impl._apply_command_modifiers(
        args=FireJobArgs(path=".", optimized=True, watch=True, git_pull=True, PathExport=True),
        command="python app.py",
        choice_file=choice_file,
        repo_root=repo_root,
        randstr_func=lambda _length: "seed",
    )

    assert fire_command == f"uv run python -m fire {choice_file} run --limit=2"
    assert f"cd {choice_file.parent}" in streamlit_command
    assert "streamlit run app.py" in streamlit_command
    assert modified_command.startswith(f"export PYTHONPATH={repo_root}\n")
    assert f"git -C {choice_file.parent} pull" in modified_command
    assert "watchexec --restart --exts py,sh,ps1 python -OO app.py" in modified_command


def test_route_builds_command_and_hands_off_to_shell_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    resolved_choice_file = tmp_path.joinpath("job.py")
    repo_root = tmp_path.joinpath("repo")
    resolved_choice_file.write_text("""print("job")\n""", encoding="utf-8")
    repo_root.mkdir()
    handed_off: list[tuple[str, bool]] = []

    def fake_get_choice_file(path: str, suffixes: set[str] | None, search_root: Path | None) -> Path:
        assert path == "job.py"
        assert suffixes is None
        assert search_root == tmp_path
        return resolved_choice_file

    def fake_build_command(
        args: FireJobArgs,
        choice_file: Path,
        choice_function: str | None,
        kwargs_dict: dict[str, object],
        repo_root_arg: Path | None,
        fire_args: str,
        randstr_func,
    ) -> str:
        assert args.path == "job.py"
        assert choice_file == resolved_choice_file
        assert choice_function == "run"
        assert kwargs_dict == {"count": 2}
        assert repo_root_arg == repo_root
        assert fire_args == "--limit=2"
        assert randstr_func(4) == "seed"
        return "python demo.py"

    def fake_apply_command_modifiers(args: FireJobArgs, command: str, choice_file: Path, repo_root_arg: Path | None, randstr_func) -> str:
        assert args.path == "job.py"
        assert command == "python demo.py"
        assert choice_file == resolved_choice_file
        assert repo_root_arg == repo_root
        assert randstr_func(4) == "seed"
        return "python demo.py --wrapped"

    def fake_exit_then_run_shell_script(script: str, strict: bool = False) -> None:
        handed_off.append((script, strict))

    monkeypatch.setattr(fire_jobs_impl, "_get_search_root", lambda root_repo: tmp_path)
    monkeypatch.setattr(path_helper, "get_choice_file", fake_get_choice_file)
    monkeypatch.setattr(accessories, "get_repo_root", lambda path: repo_root)
    monkeypatch.setattr(accessories, "randstr", lambda length: "seed")
    monkeypatch.setattr(fire_jobs_impl, "_prepare_kwargs", lambda args, choice_file: {"count": 2})
    monkeypatch.setattr(fire_jobs_impl, "_choose_function", lambda choose_function, function, choice_file, kwargs_dict: "run")
    monkeypatch.setattr(fire_jobs_impl, "_build_command", fake_build_command)
    monkeypatch.setattr(fire_jobs_impl, "_apply_command_modifiers", fake_apply_command_modifiers)
    monkeypatch.setattr(code_module, "exit_then_run_shell_script", fake_exit_then_run_shell_script)

    fire_jobs_impl.route(args=FireJobArgs(path="job.py", function="run"), fire_args="--limit=2")

    assert handed_off == [("python demo.py --wrapped", False)]
