

from importlib import resources

import stackops.scripts as scripts_package


def test_scripts_package_contains_expected_subdirectories() -> None:
    package_root = resources.files(scripts_package)

    for directory_name in ("linux", "nu", "python", "windows"):
        assert package_root.joinpath(directory_name).is_dir()
