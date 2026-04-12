from __future__ import annotations

from typing import ClassVar, cast

import pytest

import machineconfig.jobs.installer.python_scripts.dubdb_adbc as duckdb_script
from machineconfig.utils.schemas.installer.installer_types import InstallerData


DUMMY_INSTALLER_DATA = cast(InstallerData, {"appName": "ignored"})


class InstallerSpy:
    instances: ClassVar[list["InstallerSpy"]] = []

    def __init__(self, installer_data: InstallerData) -> None:
        self.installer_data = installer_data
        self.installed_versions: list[str | None] = []
        type(self).instances.append(self)

    def install(self, version: str | None) -> None:
        self.installed_versions.append(version)


def test_main_uses_duckdb_installer_data(monkeypatch: pytest.MonkeyPatch) -> None:
    InstallerSpy.instances.clear()
    monkeypatch.setattr(duckdb_script, "Installer", InstallerSpy)

    duckdb_script.main(installer_data=DUMMY_INSTALLER_DATA, version="1.2.3", update=False)

    assert len(InstallerSpy.instances) == 1
    assert InstallerSpy.instances[0].installer_data == duckdb_script.DUCKDB_INSTALLER_DATA
    assert InstallerSpy.instances[0].installed_versions == ["1.2.3"]
