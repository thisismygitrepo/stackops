

from pathlib import Path

import stackops.scripts.python.helpers.helpers_seek.scripts_macos as scripts_macos


def test_macos_seek_script_reference_exists() -> None:
    package_dir = Path(scripts_macos.__file__).resolve().parent

    assert package_dir.joinpath(scripts_macos.FZFG_PATH_REFERENCE).is_file()
