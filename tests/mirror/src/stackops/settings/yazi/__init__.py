from __future__ import annotations

from pathlib import Path

import pytest

from stackops.settings import yazi


MODULE_DIR = Path(yazi.__file__).resolve().parent


@pytest.mark.parametrize(
    "relative_path",
    [
        yazi.INIT_PATH_REFERENCE,
        yazi.KEYMAP_DARWIN_PATH_REFERENCE,
        yazi.KEYMAP_LINUX_PATH_REFERENCE,
        yazi.KEYMAP_WINDOWS_PATH_REFERENCE,
        yazi.THEME_PATH_REFERENCE,
        yazi.YAZI_DARWIN_PATH_REFERENCE,
        yazi.YAZI_LINUX_PATH_REFERENCE,
        yazi.YAZI_WINDOWS_PATH_REFERENCE,
    ],
)
def test_yazi_path_references_point_to_existing_files(relative_path: str) -> None:
    resolved_path = MODULE_DIR.joinpath(relative_path)

    assert resolved_path.is_file()
