

from pathlib import Path

import pytest

from stackops.settings import yazi


MODULE_DIR = Path(yazi.__file__).resolve().parent
EXPECTED_UV_PREFIX = "uv run --isolated --no-project --python 3.14"


@pytest.mark.parametrize(
    "relative_path",
    [
        yazi.KEYMAP_DARWIN_PATH_REFERENCE,
        yazi.KEYMAP_LINUX_PATH_REFERENCE,
        yazi.KEYMAP_WINDOWS_PATH_REFERENCE,
    ],
)
def test_yazi_uv_run_bindings_use_isolated_non_project_envs(relative_path: str) -> None:
    keymap_path = MODULE_DIR / relative_path
    keymap_text = keymap_path.read_text(encoding="utf-8")
    uv_run_lines = [line.strip() for line in keymap_text.splitlines() if "uv run" in line]

    assert uv_run_lines
    assert all(EXPECTED_UV_PREFIX in line for line in uv_run_lines)
