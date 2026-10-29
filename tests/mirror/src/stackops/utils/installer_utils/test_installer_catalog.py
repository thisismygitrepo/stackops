from pathlib import Path

import pytest

from stackops.utils.installer_utils.installer_catalog import InstallerDataFileError, installer_data_file_text, load_installer_data_file
from stackops.utils.schemas.installer.installer_types import InstallerData, InstallerDataFiles


def _installer() -> InstallerData:
    return {
        "appName": "demo",
        "license": "MIT",
        "repoURL": "https://github.com/owner/demo",
        "lastCommitDate": "2026-08-15T12:30:45Z",
        "doc": "demo tool",
        "comment": "pinned: upstream ships no arm64 builds",
        "categoryLabels": ["system-setup"],
        "fileNamePattern": {
            "amd64": {"linux": 'demo "{version}" # linux.tar.gz', "darwin": None, "windows": "yes"},
            "arm64": {"linux": {"apk": "sudo apk add demo", "apt": None, "dnf": None, "pacman": None}, "darwin": None, "windows": None},
        },
    }


def test_written_catalog_round_trips_with_schema_header_and_comment(tmp_path: Path) -> None:
    catalog_path = tmp_path.joinpath("installer_data.yaml")
    catalog: InstallerDataFiles = {"version": "4", "installers": [_installer()]}

    catalog_text = installer_data_file_text(path=catalog_path, catalog=catalog)
    catalog_path.write_text(catalog_text, encoding="utf-8")

    assert catalog_text.startswith("# yaml-language-server: $schema=./installer_data.schema.json\n")
    assert load_installer_data_file(path=catalog_path) == catalog


@pytest.mark.parametrize(
    ("catalog_text", "error_pattern"),
    [
        ("version: 4\ninstallers: []\n", "'version' must be a non-empty quoted string"),
        (
            """version: "4"
installers:
  - appName: demo
    license: MIT
    repoURL: https://github.com/owner/demo
    lastCommitDate: 2026-08-15T12:30:45Z
    doc: demo tool
    categoryLabels: [system-setup]
    fileNamePattern:
      amd64: {linux: demo.tar.gz, darwin: null, windows: null}
      arm64: {linux: null, darwin: null, windows: null}
""",
            r"lastCommitDate must be a non-empty string \(quote YAML values",
        ),
    ],
)
def test_unquoted_yaml_scalars_are_rejected(tmp_path: Path, catalog_text: str, error_pattern: str) -> None:
    catalog_path = tmp_path.joinpath("installer_data.yaml")
    catalog_path.write_text(catalog_text, encoding="utf-8")

    with pytest.raises(InstallerDataFileError, match=error_pattern):
        load_installer_data_file(path=catalog_path)


def test_json_catalog_paths_are_rejected(tmp_path: Path) -> None:
    catalog_path = tmp_path.joinpath("installer_data.json")
    catalog_path.write_text("""{"version": "4", "installers": []}""", encoding="utf-8")

    with pytest.raises(InstallerDataFileError, match="must be YAML with the '.yaml' suffix"):
        load_installer_data_file(path=catalog_path)
