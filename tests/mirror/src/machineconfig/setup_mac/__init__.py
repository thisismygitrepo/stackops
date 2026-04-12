from __future__ import annotations

from pathlib import Path

import machineconfig.setup_mac as target_module
from machineconfig.setup_mac import UV_PATH_REFERENCE


def test_setup_mac_assets_exist() -> None:
    module_file = target_module.__file__
    assert module_file is not None
    module_dir = Path(module_file).resolve().parent

    assert module_dir.joinpath(UV_PATH_REFERENCE).is_file()
