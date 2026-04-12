from __future__ import annotations

from pathlib import Path

import machineconfig.settings.zellij.layouts as target_module
from machineconfig.settings.zellij.layouts import (
    HIST_PATH_REFERENCE,
    PANES_PATH_REFERENCE,
    STACKED_PANES_PATH_REFERENCE,
    ST_PATH_REFERENCE,
    ST2_PATH_REFERENCE,
)


def test_layout_assets_exist() -> None:
    module_file = target_module.__file__
    assert module_file is not None
    module_dir = Path(module_file).resolve().parent

    for relative_path in (
        HIST_PATH_REFERENCE,
        PANES_PATH_REFERENCE,
        STACKED_PANES_PATH_REFERENCE,
        ST_PATH_REFERENCE,
        ST2_PATH_REFERENCE,
    ):
        assert module_dir.joinpath(relative_path).is_file()
