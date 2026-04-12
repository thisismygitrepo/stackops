from __future__ import annotations

import runpy
from pathlib import Path
from types import FunctionType
from typing import cast

import pytest

from machineconfig.cluster.remote.job_params import JobParams
from machineconfig.cluster.remote.models import WorkloadParams


class _HelperCallable:
    def method(self, *, value: int) -> int:
        return value + 1


def test_from_callable_detects_class_qualname_and_repo_relative_path() -> None:
    params = JobParams.from_callable(_HelperCallable.method)

    assert params.func_class == "_HelperCallable"
    assert params.func_name == "method"
    assert Path(params.repo_path_rh).expanduser().joinpath(params.file_path_r).exists()


def test_from_callable_supports_run_path_functions(tmp_path: Path) -> None:
    script_path = tmp_path / "task_script.py"
    script_path.write_text("def demo() -> int:\n    return 7\n", encoding="utf-8")
    namespace = runpy.run_path(str(script_path))
    func = cast(FunctionType, namespace["demo"])

    params = JobParams.from_callable(func)

    assert params.func_module == "task_script.py"
    assert params.file_path_r == "task_script.py"
    assert Path(params.repo_path_rh).expanduser() == tmp_path


def test_from_callable_rejects_main_module_functions() -> None:
    namespace: dict[str, object] = {"__name__": "__main__"}
    exec("def main_only() -> int:\n    return 1\n", namespace)
    func = cast(FunctionType, namespace["main_only"])

    with pytest.raises(ValueError, match="__main__"):
        JobParams.from_callable(func)


def test_get_execution_line_renders_parallel_try_wrapper() -> None:
    params = JobParams(
        description="",
        ssh_repr="",
        ssh_repr_remote="",
        error_message="",
        session_name="",
        tab_name="",
        file_manager_path="",
        repo_path_rh="~/repo",
        file_path_rh="~/repo/pkg/task.py",
        file_path_r="pkg/task.py",
        func_module="pkg.task",
        func_class=None,
        func_name="run_task",
    )
    workload_params = WorkloadParams.default()

    execution_line = params.get_execution_line(workload_params=workload_params, parallelize=True, wrap_in_try_except=True)

    assert "from pkg.task import run_task as func" in execution_line
    assert "ProcessPoolExecutor" in execution_line
    assert "split_params = [WorkloadParams(**kw) for kw in kwargs_workload]" in execution_line
    assert "params.error_message = str(e)" in execution_line


def test_script_execution_line_uses_exec_and_installable_checks_setup_py(tmp_path: Path) -> None:
    setup_py = tmp_path / "setup.py"
    setup_py.write_text("from setuptools import setup\n", encoding="utf-8")
    params = JobParams.empty()
    params.repo_path_rh = str(tmp_path)
    params.file_path_rh = str(tmp_path / "script.py")
    params.func_module = "script"

    execution_line = params.get_execution_line(workload_params=None, parallelize=False, wrap_in_try_except=False)

    assert "exec(Path(r'" in execution_line
    assert params.is_installable() is True
