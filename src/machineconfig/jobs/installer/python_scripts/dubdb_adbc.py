from typing import TYPE_CHECKING

from machineconfig.jobs.installer.python_scripts.main_protocol import (
    InstallerPythonScriptMain,
)
from machineconfig.utils.installer_utils.installer_class import Installer
from machineconfig.utils.schemas.installer.installer_types import InstallerData


DUCKDB_INSTALLER_DATA: InstallerData = {
    "appName": "libduckdb.so",
    "license": "MIT",
    "repoURL": "https://github.com/duckdb/duckdb",
    "doc": "🗃️ An in-process SQL OLAP database management system",
    "fileNamePattern": {
        "amd64": {
            "linux": "libduckdb-linux-amd64.zip",
            "darwin": None,
            "windows": None,
        },
        "arm64": {
            "linux": "libduckdb-linux-arm64.zip",
            "darwin": None,
            "windows": None,
        },
    },
}


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    _ = installer_data, update
    installer = Installer(installer_data=DUCKDB_INSTALLER_DATA)
    installer.install(version=version)


if __name__ == "__main__":
    if TYPE_CHECKING:
        _main_protocol_check: InstallerPythonScriptMain = main
