from pathlib import Path
from types import ModuleType

import machineconfig.settings.shells.kitty as kitty


def _module_path(module: ModuleType) -> Path:
    module_file = module.__file__
    assert module_file is not None
    return Path(module_file).resolve()


def test_kitty_path_reference_points_to_shipped_config() -> None:
    config_path = _module_path(kitty).parent / kitty.KITTY_PATH_REFERENCE

    assert config_path.is_file()
    assert config_path.read_text(encoding="utf-8").strip()
