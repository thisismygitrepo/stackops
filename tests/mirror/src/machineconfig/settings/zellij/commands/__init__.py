from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.settings.zellij import commands


MODULE_DIR = Path(commands.__file__).resolve().parent


@pytest.mark.parametrize("relative_path", [commands.MONITOR_PATH_REFERENCE, commands.STANDARD_PANES_PATH_REFERENCE])
def test_zellij_command_path_references_point_to_existing_files(relative_path: str) -> None:
    resolved_path = MODULE_DIR.joinpath(relative_path)

    assert resolved_path.is_file()
