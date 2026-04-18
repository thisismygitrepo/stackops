from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pytest

import stackops.jobs.installer.python_scripts.docker as docker_script
from stackops.utils.schemas.installer.installer_types import InstallerData


DUMMY_INSTALLER_DATA = cast(InstallerData, {})


@dataclass(frozen=True)
class CompletedProcessStub:
    returncode: int


@dataclass(frozen=True)
class PrintedCode:
    code: str
    lexer: str
    desc: str


def test_main_linux_uses_linux_script_and_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[PrintedCode] = []
    shell_calls: list[tuple[str, bool, bool]] = []

    def fake_print_code(code: str, lexer: str, desc: str) -> None:
        printed.append(PrintedCode(code=code, lexer=lexer, desc=desc))

    def fake_run_shell_script(script: str, display_script: bool, clean_env: bool) -> CompletedProcessStub:
        shell_calls.append((script, display_script, clean_env))
        return CompletedProcessStub(returncode=7)

    monkeypatch.setattr(docker_script.platform, "system", lambda: "Linux")
    monkeypatch.setattr(docker_script, "print_code", fake_print_code)
    monkeypatch.setattr(docker_script, "run_shell_script", fake_run_shell_script)

    with pytest.raises(RuntimeError, match="Docker installation failed with exit code 7"):
        docker_script.main(installer_data=DUMMY_INSTALLER_DATA, version=None, update=False)

    assert len(printed) == 1
    assert printed[0].lexer == "shell"
    assert "download.docker.com/linux" in printed[0].code
    assert "docker-ce" in printed[0].code
    assert shell_calls == [(printed[0].code, True, False)]


def test_main_windows_is_not_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(docker_script.platform, "system", lambda: "Windows")

    with pytest.raises(NotImplementedError, match="Docker installation is not supported on Windows"):
        docker_script.main(installer_data=DUMMY_INSTALLER_DATA, version="latest", update=False)
