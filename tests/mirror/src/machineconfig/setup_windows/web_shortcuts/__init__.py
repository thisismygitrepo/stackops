from __future__ import annotations

from pathlib import Path

import machineconfig.setup_windows.web_shortcuts as target_module
from machineconfig.setup_windows.web_shortcuts import (
    INTERACTIVE_PATH_REFERENCE,
    LIVE_FROM_GITHUB_PATH_REFERENCE,
    QUICK_INIT_PATH_REFERENCE,
)


def test_windows_web_shortcut_assets_exist() -> None:
    module_file = target_module.__file__
    assert module_file is not None
    module_dir = Path(module_file).resolve().parent

    for relative_path in (
        INTERACTIVE_PATH_REFERENCE,
        LIVE_FROM_GITHUB_PATH_REFERENCE,
        QUICK_INIT_PATH_REFERENCE,
    ):
        assert module_dir.joinpath(relative_path).is_file()
