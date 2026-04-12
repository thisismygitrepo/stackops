from __future__ import annotations

from pathlib import Path

import machineconfig.utils.cloud.onedrive as target_module
from machineconfig.utils.cloud.onedrive import README_PATH_REFERENCE


def test_onedrive_readme_path_reference_exists() -> None:
    module_file = target_module.__file__
    assert module_file is not None
    module_dir = Path(module_file).resolve().parent

    assert module_dir.joinpath(README_PATH_REFERENCE).is_file()
