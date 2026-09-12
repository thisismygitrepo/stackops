import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FireEnvironment:
    project_root: Path
    directory: Path
    interpreter: Path


def resolve_fire_environment(choice_file: Path, repo_root: Path | None) -> FireEnvironment | None:
    project_root: Path | None = None
    for directory in choice_file.absolute().parents:
        if (directory / "pyproject.toml").is_file():
            project_root = directory
            break
        if directory == repo_root:
            break
    if project_root is None:
        return None

    environment_directory = (project_root / ".venv").resolve()
    owner_root = environment_directory.parent
    if environment_directory.name != ".venv" or not (owner_root / "pyproject.toml").is_file():
        raise ValueError(f"""Project environment {environment_directory} must belong to a project with its own pyproject.toml and .venv.""")
    interpreter = environment_directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not (environment_directory / "pyvenv.cfg").is_file() or not interpreter.is_file():
        raise ValueError(f"""Fire requires a prepared environment at {environment_directory}. Run uv sync --project {owner_root} before launching jobs.""")
    return FireEnvironment(project_root=owner_root, directory=environment_directory, interpreter=interpreter)


def build_uv_run_arguments(environment: FireEnvironment | None, frozen: bool) -> list[str]:
    arguments = ["uv", "run", "--no-sync", "--no-active"]
    if frozen:
        arguments.append("--frozen")
    if environment is None:
        arguments.append("--no-project")
    else:
        arguments.extend(["--project", str(environment.project_root), "--python", str(environment.interpreter)])
    return arguments


def build_uv_run_shell_prefix(environment: FireEnvironment | None, frozen: bool, cmd: bool) -> str:
    arguments = build_uv_run_arguments(environment=environment, frozen=frozen)
    if os.name == "nt":
        if cmd:
            environment_value = "" if environment is None else str(environment.directory)
            return f"""set "UV_PROJECT_ENVIRONMENT={environment_value}" && {subprocess.list2cmdline(arguments)}"""
        command = " ".join("'" + argument.replace("'", "''") + "'" for argument in arguments)
        environment_value = "$null" if environment is None else "'" + str(environment.directory).replace("'", "''") + "'"
        return f"""$env:UV_PROJECT_ENVIRONMENT = {environment_value}; & {command}"""
    if environment is None:
        return shlex.join(["env", "-u", "UV_PROJECT_ENVIRONMENT", *arguments])
    return shlex.join(["env", f"""UV_PROJECT_ENVIRONMENT={environment.directory}""", *arguments])
