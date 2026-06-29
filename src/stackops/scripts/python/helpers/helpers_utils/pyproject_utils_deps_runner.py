from pathlib import Path
import os
import subprocess

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
    DependencyBackend,
    DependencyCheckContext,
)

BACKEND_PACKAGE_NAMES: dict[DependencyBackend, str] = {
    "pyan": "pyan3",
    "pydeps": "pydeps",
}
BACKEND_RUNNER_SCRIPT = """import subprocess
import sys


def main() -> None:
    completed = subprocess.run(sys.argv[1:], check=False)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
"""


def run_backend_command(
    context: DependencyCheckContext,
    backend: DependencyBackend,
    backend_command: list[str],
) -> subprocess.CompletedProcess[str]:
    runner_script = _write_backend_runner_script(repo_root=context.repo_root)
    uv_command = [
        "uv",
        "run",
        "--with",
        BACKEND_PACKAGE_NAMES[backend],
        "python",
        runner_script.as_posix(),
        *backend_command,
    ]
    completed = subprocess.run(
        uv_command,
        cwd=context.repo_root,
        capture_output=True,
        check=False,
        env=_build_backend_environment(repo_root=context.repo_root),
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{backend} failed with exit code {completed.returncode}.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def _write_backend_runner_script(repo_root: Path) -> Path:
    runner_directory = repo_root / ".ai" / "tmp_scripts" / "check_deps"
    runner_directory.mkdir(parents=True, exist_ok=True)
    runner_script = runner_directory / "backend_runner.py"
    if runner_script.exists() is False or runner_script.read_text(encoding="utf-8") != BACKEND_RUNNER_SCRIPT:
        runner_script.write_text(BACKEND_RUNNER_SCRIPT, encoding="utf-8")
    return runner_script


def _build_backend_environment(repo_root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    src_path = repo_root / "src"
    if src_path.is_dir():
        existing_pythonpath = environment.get("PYTHONPATH")
        environment["PYTHONPATH"] = src_path.as_posix() if existing_pythonpath is None else f"{src_path.as_posix()}{os.pathsep}{existing_pythonpath}"
    return environment
