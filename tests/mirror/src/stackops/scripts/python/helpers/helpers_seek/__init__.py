

from pathlib import Path

import stackops.scripts.python.helpers.helpers_seek as helpers_seek


def test_top_level_seek_path_references_exist() -> None:
    package_dir = Path(helpers_seek.__file__).resolve().parent

    assert package_dir.joinpath(helpers_seek.FZFG_LINUX_PATH_REFERENCE).is_file()
    assert package_dir.joinpath(helpers_seek.FZFG_WINDOWS_PATH_REFERENCE).is_file()
    assert package_dir.joinpath(helpers_seek.FZFG_MACOS_PATH_REFERENCE).is_file()
