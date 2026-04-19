

import importlib
from pathlib import Path


def test_helpers_cloud_package_contains_expected_modules() -> None:
    module = importlib.import_module("stackops.scripts.python.helpers.helpers_cloud")
    package_dir = Path(module.__file__ or "").parent

    assert package_dir.joinpath("cloud_copy.py").is_file()
    assert package_dir.joinpath("cloud_helpers.py").is_file()
    assert package_dir.joinpath("cloud_mount.py").is_file()
