

from pathlib import Path

import stackops.scripts.python.helpers.helpers_seek.scripts_linux as scripts_linux


def test_linux_seek_script_references_exist() -> None:
    package_dir = Path(scripts_linux.__file__).resolve().parent

    assert package_dir.joinpath(scripts_linux.FZFG_PATH_REFERENCE).is_file()
    assert package_dir.joinpath(scripts_linux.SEARCH_WITH_CONTEXT_PATH_REFERENCE).is_file()
