from __future__ import annotations

from pathlib import Path

import stackops.setup_linux as target_module
from stackops.setup_linux import APPS_DESKTOP_PATH_REFERENCE, UV_PATH_REFERENCE


def test_setup_linux_assets_exist() -> None:
    module_file = target_module.__file__
    assert module_file is not None
    module_dir = Path(module_file).resolve().parent

    for relative_path in (APPS_DESKTOP_PATH_REFERENCE, UV_PATH_REFERENCE):
        assert module_dir.joinpath(relative_path).is_file()
