from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

import stackops.jobs.installer.linux_scripts as linux_scripts
import stackops.jobs.installer.powershell_scripts as powershell_scripts
import stackops.jobs.installer.python_scripts.sysabc as sysabc
import stackops.utils.code as code_utils
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.installer.installer_types import InstallerData


def _installer_data() -> InstallerData:
    return cast(InstallerData, {})


@pytest.mark.parametrize(
    ("module_obj", "path_reference", "suffix"),
    [
        (powershell_scripts, powershell_scripts.SYSABC_PATH_REFERENCE, ".ps1"),
        (linux_scripts, linux_scripts.SYSABC_UBUNTU_PATH_REFERENCE, ".sh"),
        (linux_scripts, linux_scripts.SYSABC_MACOS_PATH_REFERENCE, ".sh"),
    ],
)
def test_platform_script_references_exist(module_obj: ModuleType, path_reference: str, suffix: str) -> None:
    script_path = get_path_reference_path(module=module_obj, path_reference=path_reference)

    assert script_path.is_file()
    assert script_path.suffix == suffix


@pytest.mark.parametrize(("platform_name", "file_name"), [("Windows", "sysabc.ps1"), ("Linux", "sysabc.sh"), ("Darwin", "sysabc.sh")])
def test_main_reads_platform_script_and_executes_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform_name: str, file_name: str) -> None:
    script_path = tmp_path / file_name
    script_path.write_text("echo sysabc", encoding="utf-8")
    printed_programs: list[tuple[str, str, str]] = []
    executed_programs: list[tuple[str, bool, bool]] = []

    def fake_get_path_reference_path(*, module: object, path_reference: str) -> Path:
        _ = module, path_reference
        return script_path

    def fake_print_code(code: str, lexer: str, desc: str) -> None:
        printed_programs.append((code, lexer, desc))

    def fake_run_shell_script(program: str, display_script: bool, clean_env: bool) -> None:
        executed_programs.append((program, display_script, clean_env))

    monkeypatch.setattr(sysabc.platform, "system", lambda: platform_name)
    monkeypatch.setattr(sysabc, "get_path_reference_path", fake_get_path_reference_path)
    monkeypatch.setattr(code_utils, "print_code", fake_print_code)
    monkeypatch.setattr(code_utils, "run_shell_script", fake_run_shell_script)

    sysabc.main(installer_data=_installer_data(), version=None, update=False)

    assert printed_programs == [("echo sysabc", "shell", "Installation Script Preview")]
    assert executed_programs == [("echo sysabc", True, False)]


def test_unsupported_platform_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sysabc.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Unsupported platform: Plan9"):
        sysabc.main(installer_data=_installer_data(), version=None, update=False)
