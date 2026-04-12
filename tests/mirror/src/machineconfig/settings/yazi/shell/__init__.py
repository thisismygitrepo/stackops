from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.settings.yazi import shell


MODULE_DIR = Path(shell.__file__).resolve().parent


@pytest.mark.parametrize(
    "relative_path",
    [
        shell.YAZI_CD_PS1_PATH_REFERENCE,
        shell.YAZI_CD_SH_PATH_REFERENCE,
    ],
)
def test_yazi_shell_path_references_point_to_existing_files(relative_path: str) -> None:
    resolved_path = MODULE_DIR.joinpath(relative_path)

    assert resolved_path.is_file()
