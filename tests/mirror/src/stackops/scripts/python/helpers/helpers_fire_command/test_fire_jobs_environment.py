import os
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_fire_command import fire_jobs_impl, fire_jobs_route_helper
from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_environment import build_uv_run_shell_prefix, resolve_fire_environment


def create_project(directory: Path, prepare_environment: bool) -> Path:
    subprocess.run(
        ["uv", "init", "--bare", "--no-config", "--no-workspace", "--vcs", "none", "--name", "fire-test", str(directory)],
        cwd=directory.parent,
        capture_output=True,
        text=True,
        check=True,
    )
    if prepare_environment:
        subprocess.run(
            ["uv", "venv", "--no-config", "--no-project", "--python", sys.executable, str(directory / ".venv")],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True,
        )
    return directory


@pytest.mark.skipif(os.name == "nt", reason="Executes the POSIX shell handoff.")
@pytest.mark.parametrize("frozen", [False, True])
def test_shared_environment_launches_use_owner_without_syncing(tmp_path: Path, frozen: bool) -> None:
    owner = create_project(directory=tmp_path / "owner ' $(false)", prepare_environment=True)
    source = create_project(directory=tmp_path / "source", prepare_environment=False)
    foreign = create_project(directory=tmp_path / "foreign", prepare_environment=True)
    (source / ".venv").symlink_to(owner / ".venv", target_is_directory=True)
    subprocess.run(
        ["uv", "add", "--no-config", "--offline", "--project", str(owner), "--frozen", "fire-test-must-never-resolve"],
        cwd=owner,
        capture_output=True,
        text=True,
        check=True,
    )
    sentinel = owner / ".venv" / "installed-package-sentinel"
    sentinel.write_text("leave installed packages unchanged", encoding="utf-8")
    initial_mtime = sentinel.stat().st_mtime_ns
    probe = source / "probe.py"
    probe.write_text("import os, sys\nprint(sys.prefix)\nprint(os.environ['VIRTUAL_ENV'])\n", encoding="utf-8")
    process_environment = os.environ | {
        "UV_PROJECT_ENVIRONMENT": str(foreign / ".venv"),
        "VIRTUAL_ENV": str(foreign / ".venv"),
        "UV_PYTHON": str(foreign / ".venv" / "bin/python"),
        "UV_OFFLINE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }

    def launch(project: Path) -> subprocess.CompletedProcess[str]:
        environment = resolve_fire_environment(choice_file=project / "probe.py", repo_root=project)
        prefix = build_uv_run_shell_prefix(environment=environment, frozen=frozen, cmd=False)
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-c", f"""{prefix} python {shlex.quote(str(probe))}"""],
            cwd=foreign,
            env=process_environment,
            capture_output=True,
            text=True,
            check=True,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(launch, [source, owner, source, owner]))

    for result in results:
        assert result.stdout.splitlines() == [str(owner / ".venv"), str(owner / ".venv")]
        assert "Installed" not in result.stderr
        assert "Uninstalled" not in result.stderr
    assert sentinel.stat().st_mtime_ns == initial_mtime
    assert sentinel.read_text(encoding="utf-8") == "leave installed packages unchanged"
    assert not (owner / "uv.lock").exists()
    assert not (source / "uv.lock").exists()


@pytest.mark.parametrize("shared", [False, True])
def test_missing_environment_fails_without_creating_one(tmp_path: Path, shared: bool) -> None:
    project = create_project(directory=tmp_path / "project", prepare_environment=False)
    if shared:
        owner = create_project(directory=tmp_path / "owner", prepare_environment=False)
        (project / ".venv").symlink_to(owner / ".venv", target_is_directory=True)
    with pytest.raises(ValueError, match="Fire requires a prepared environment"):
        resolve_fire_environment(choice_file=project / "script.py", repo_root=project)
    assert not (project / ".venv").exists()
    assert not (project / "uv.lock").exists()


def test_shared_environment_requires_an_owner_project(tmp_path: Path) -> None:
    source = create_project(directory=tmp_path / "source", prepare_environment=False)
    unrelated_environment = tmp_path / "unowned" / ".venv"
    unrelated_environment.mkdir(parents=True)
    (source / ".venv").symlink_to(unrelated_environment, target_is_directory=True)
    with pytest.raises(ValueError, match="must belong to a project"):
        resolve_fire_environment(choice_file=source / "script.py", repo_root=source)


def test_nested_python_project_owns_its_environment(tmp_path: Path) -> None:
    repository = create_project(directory=tmp_path / "repository", prepare_environment=True)
    project = create_project(directory=repository / "nested", prepare_environment=True)
    environment = resolve_fire_environment(choice_file=project / "src" / "script.py", repo_root=repository)
    assert environment is not None
    assert environment.project_root == project
    assert environment.directory == project / ".venv"


def test_standalone_script_does_not_discover_caller_project(tmp_path: Path) -> None:
    environment = resolve_fire_environment(choice_file=tmp_path / "script.py", repo_root=tmp_path)
    assert environment is None
    assert "--no-project" in build_uv_run_shell_prefix(environment=environment, frozen=False, cmd=False)


@pytest.mark.skipif(os.name == "nt", reason="Parses the POSIX shell handoff.")
@pytest.mark.parametrize("optimized", [False, True])
def test_streamlit_preserves_dashboard_lifecycle_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, optimized: bool) -> None:
    owner = create_project(directory=tmp_path / "owner", prepare_environment=True)
    source = create_project(directory=tmp_path / "source", prepare_environment=False)
    (source / ".venv").symlink_to(owner / ".venv", target_is_directory=True)

    def dashboard_command(choice_file: Path) -> str:
        assert choice_file == source / "app.py"
        return "python -m stackops.utils.dashboard_streamlit --port 41000 --"

    monkeypatch.setattr(fire_jobs_route_helper, "get_command_streamlit", dashboard_command)
    command = fire_jobs_impl._build_python_exe_line(
        module=False, cmd=False, interactive=False, optimized=optimized, frozen=False, streamlit=True, jupyter=False,
        choice_file=source / "app.py", repo_root=source
    )
    tokens = shlex.split(command)
    assert tokens[tokens.index("--project") + 1] == str(owner)
    assert tokens[tokens.index("--python") + 1] == str(owner / ".venv/bin/python")
    interpreter_arguments = ["python", "-OO"] if optimized else ["python"]
    dashboard_arguments = [*interpreter_arguments, "-m", "stackops.utils.dashboard_streamlit", "--port", "41000", "--"]
    assert tokens[-len(dashboard_arguments):] == dashboard_arguments
    assert "--no-sync" in tokens


@pytest.mark.skipif(os.name == "nt", reason="Parses the POSIX shell handoff.")
@pytest.mark.parametrize("valid_notebook", [False, True])
def test_marimo_check_conversion_and_editor_share_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, valid_notebook: bool
) -> None:
    from stackops.utils import code

    owner = create_project(directory=tmp_path / "owner", prepare_environment=True)
    source = create_project(directory=tmp_path / "source", prepare_environment=False)
    (source / ".venv").symlink_to(owner / ".venv", target_is_directory=True)
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", str(tmp_path / "foreign"))
    scripts: list[str] = []

    def check_notebook(
        args: list[str], capture_output: bool, text: bool, check: bool, env: dict[str, str]
    ) -> subprocess.CompletedProcess[str]:
        assert capture_output and text and not check
        assert args[args.index("--project") + 1] == str(owner)
        assert "--no-sync" in args
        assert env["UV_PROJECT_ENVIRONMENT"] == str(owner / ".venv")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="" if valid_notebook else "not a valid notebook", stderr="")

    def capture_script(script: str) -> None:
        assert script.strip()
        scripts.append(script)

    monkeypatch.setattr(fire_jobs_impl.subprocess, "run", check_notebook)
    monkeypatch.setattr(code, "exit_then_run_shell_script", capture_script)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    fire_jobs_impl._handle_marimo(choice_file=source / "notebook.py", repo_root=source, randstr_func=lambda _length: "test", jit=False)

    commands = [shlex.split(line) for line in scripts[0].splitlines() if line.startswith("env ")]
    assert len(commands) == (1 if valid_notebook else 2)
    for command in commands:
        assert command[1] == f"""UV_PROJECT_ENVIRONMENT={owner / '.venv'}"""
        assert command[command.index("--project") + 1] == str(owner)
        assert "--no-sync" in command
