import re
from pathlib import Path


YAZI_SETTINGS_DIR = Path("src/stackops/settings/yazi")
KEYMAP_PATHS: tuple[Path, ...] = (
    YAZI_SETTINGS_DIR / "keymap_linux.toml",
    YAZI_SETTINGS_DIR / "keymap_darwin.toml",
    YAZI_SETTINGS_DIR / "keymap_windows.toml",
)
ISOLATED_UV_PYTHON_PATTERN = re.compile(r"uv run --isolated --no-project --python 3\.14(?! --with stackops)")


def test_yazi_isolated_python_keymaps_include_stackops_dependency() -> None:
    for keymap_path in KEYMAP_PATHS:
        keymap_text = keymap_path.read_text(encoding="utf-8")
        assert ISOLATED_UV_PYTHON_PATTERN.search(keymap_text) is None, keymap_path
