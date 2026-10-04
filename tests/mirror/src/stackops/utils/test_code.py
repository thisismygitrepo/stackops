import os
from pathlib import Path
import shlex
import subprocess

import pytest

from stackops.utils import code


pytestmark = pytest.mark.skipif(os.name == "nt", reason="Requires Bash execution and POSIX command parsing.")


def _write_worker_imports(output_path: str) -> None:
    from pathlib import Path

    import stackops.utils.code as imported_code
    from vt import Client

    source_path = imported_code.__file__
    assert source_path is not None
    Path(output_path).write_text(f"""{Path(source_path).resolve()}\n{Client.__name__}""", encoding="utf-8")


def test_serialized_worker_imports_parent_stackops_outside_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "worker-imports.txt"
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    shell_script, _python_file = code.get_shell_script_running_lambda_function(
        lambda: _write_worker_imports(output_path=str(output_path)),
        uv_with=["vt-py"],
        uv_project_dir=None,
        uv_run_flags="",
    )
    worker_environment = dict(os.environ)
    for variable in ("VIRTUAL_ENV", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT", "UV_PYTHON"):
        worker_environment.pop(variable, None)

    result = subprocess.run(
        ["bash", "-c", shell_script],
        cwd=Path(tmp_path.anchor),
        env=worker_environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output_path.read_text(encoding="utf-8").splitlines() == [str(Path(code.__file__).resolve()), "Client"]


def test_serialized_worker_preserves_explicit_project_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    project_dir = tmp_path / "worker project"
    shell_script, _python_file = code.get_shell_script_running_lambda_function(
        lambda: _write_worker_imports(output_path=str(tmp_path / "worker-imports.txt")),
        uv_with=["vt-py"],
        uv_project_dir=str(project_dir),
        uv_run_flags="--no-sync",
    )
    arguments = shlex.split(shell_script)

    assert arguments[arguments.index("--project") + 1] == str(project_dir)
    assert "--no-sync" in arguments
    assert "--python" not in arguments
