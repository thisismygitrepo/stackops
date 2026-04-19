

from pathlib import Path
import importlib.metadata as importlib_metadata
from typing import cast

import pytest

from stackops.jobs.installer.package_groups import PACKAGE_NAME
from stackops.utils.installer_utils import installer_runner as runner
from stackops.utils.schemas.installer.installer_types import InstallerData, InstallerDataFiles


def _make_installer(app_name: str, linux_pattern: str | None) -> InstallerData:
    return {
        "appName": app_name,
        "license": "MIT",
        "doc": f"{app_name} docs",
        "repoURL": "https://github.com/example/project",
        "fileNamePattern": {
            "amd64": {
                "linux": linux_pattern,
                "darwin": None,
                "windows": None,
            },
            "arm64": {
                "linux": linux_pattern,
                "darwin": None,
                "windows": None,
            },
        },
    }


def test_get_installers_filters_category_and_supported_platform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installer_data_files: InstallerDataFiles = {
        "version": "1",
        "installers": [
            _make_installer("KeepMe", "keep.tar.gz"),
            _make_installer("SkipMe", "skip.tar.gz"),
            _make_installer("Unsupported", None),
        ],
    }
    package_groups = cast(dict[PACKAGE_NAME, list[str]], {"termabc": ["KeepMe"]})

    monkeypatch.setattr(runner, "read_json", lambda _path: installer_data_files)
    monkeypatch.setattr(runner, "get_path_reference_path", lambda module, path_reference: Path("ignored.json"))
    monkeypatch.setattr(runner, "PACKAGE_GROUP2NAMES", package_groups)

    installers = runner.get_installers(
        os="linux",
        arch="amd64",
        which_cats=["termabc"],
    )

    assert [installer["appName"] for installer in installers] == ["KeepMe"]


def test_get_stackops_version_falls_back_to_pyproject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    package_root = repo_root / "src" / "stackops"
    module_path = package_root / "utils" / "installer_utils" / "installer_runner.py"
    module_path.parent.mkdir(parents=True)
    module_path.write_text("# test module path\n", encoding="utf-8")
    (package_root / "pyproject.toml").write_text(
        '[project]\nversion = "9.9.9"\n',
        encoding="utf-8",
    )

    def raise_package_not_found(_name: str) -> str:
        raise importlib_metadata.PackageNotFoundError()

    monkeypatch.setattr(importlib_metadata, "version", raise_package_not_found)
    monkeypatch.setattr(runner, "__file__", str(module_path))

    assert runner.get_stackops_version() == "9.9.9"
