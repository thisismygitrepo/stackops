

from pathlib import Path

import stackops.scripts.python.helpers.helpers_seek.scripts_windows as scripts_windows


def test_windows_seek_script_reference_exists() -> None:
    package_dir = Path(scripts_windows.__file__).resolve().parent

    assert package_dir.joinpath(scripts_windows.FZFG_PATH_REFERENCE).is_file()
