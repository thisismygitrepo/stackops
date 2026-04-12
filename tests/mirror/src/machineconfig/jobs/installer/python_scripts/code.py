from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

import machineconfig.jobs.installer.python_scripts.code as vscode_code
import machineconfig.utils.code as code_utils
from machineconfig.utils.schemas.installer.installer_types import InstallerData


DUMMY_INSTALLER_DATA = cast(InstallerData, {})


@dataclass(frozen=True)
class ShellScriptCall:
    script: str
    display_script: bool
    clean_env: bool


def test_main_linux_reads_repo_script_and_runs_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_script_path = tmp_path / "install.sh"
    install_script_path.write_text("echo linux\n", encoding="utf-8")
    calls: list[ShellScriptCall] = []

    def fake_get_path_reference_path(module: object, path_reference: object) -> Path:
        _ = module, path_reference
        return install_script_path

    def fake_run_shell_script(script: str, display_script: bool, clean_env: bool) -> None:
        calls.append(
            ShellScriptCall(
                script=script,
                display_script=display_script,
                clean_env=clean_env,
            )
        )

    monkeypatch.setattr(vscode_code.platform, "system", lambda: "Linux")
    monkeypatch.setattr(vscode_code, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(code_utils, "run_shell_script", fake_run_shell_script)

    vscode_code.main(
        installer_data=DUMMY_INSTALLER_DATA,
        version=None,
        update=False,
    )

    assert calls == [ShellScriptCall(script="echo linux\n", display_script=True, clean_env=False)]


def test_main_unsupported_platform_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vscode_code.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Unsupported platform: Plan9"):
        vscode_code.main(
            installer_data=DUMMY_INSTALLER_DATA,
            version="1.0.0",
            update=False,
        )
