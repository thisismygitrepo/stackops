from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.jobs.installer.python_scripts.main_protocol as main_protocol
from machineconfig.utils.schemas.installer.installer_types import InstallerData


def ok_main(
    installer_data: InstallerData,
    version: str | None,
    update: bool,
    install_lib: bool = True,
) -> None:
    _ = installer_data, version, update, install_lib


def bad_main_with_required_extra(
    installer_data: InstallerData,
    version: str | None,
    update: bool,
    install_lib: bool,
) -> None:
    _ = installer_data, version, update, install_lib


def test_load_main_accepts_optional_extra_parameters() -> None:
    loaded = main_protocol.load_installer_python_script_main(
        module_globals={"main": ok_main},
        installer_path=Path("installer.py"),
    )

    assert loaded is ok_main


def test_load_main_rejects_required_extra_parameters() -> None:
    with pytest.raises(TypeError, match="any extra parameters must be optional"):
        main_protocol.load_installer_python_script_main(
            module_globals={"main": bad_main_with_required_extra},
            installer_path=Path("installer.py"),
        )


def test_load_main_rejects_missing_entrypoint() -> None:
    with pytest.raises(
        TypeError,
        match=r"installer\.py must define main\(installer_data: InstallerData, version: str \| None, update: bool\)",
    ):
        main_protocol.load_installer_python_script_main(
            module_globals={},
            installer_path=Path("installer.py"),
        )
