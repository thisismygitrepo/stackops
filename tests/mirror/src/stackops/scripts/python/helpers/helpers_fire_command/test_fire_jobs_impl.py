import pytest

from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_impl import (
    _normalize_supported_platform_system,
    _prepend_python_jit_env,
)


def test_prepend_python_jit_env_uses_posix_export_for_linux() -> None:
    command = "uv run python script.py"

    result = _prepend_python_jit_env(command=command, platform_system="Linux")

    assert result == "export PYTHON_JIT=1\nuv run python script.py"


def test_prepend_python_jit_env_uses_posix_export_for_darwin() -> None:
    command = "uv run python script.py"

    result = _prepend_python_jit_env(command=command, platform_system="Darwin")

    assert result == "export PYTHON_JIT=1\nuv run python script.py"


def test_prepend_python_jit_env_uses_powershell_assignment_for_windows() -> None:
    command = "uv run python script.py"

    result = _prepend_python_jit_env(command=command, platform_system="Windows")

    assert result == "$env:PYTHON_JIT = '1'\nuv run python script.py"


def test_normalize_supported_platform_system_rejects_unknown_platforms() -> None:
    with pytest.raises(NotImplementedError, match="FreeBSD"):
        _normalize_supported_platform_system(platform_system="FreeBSD")
