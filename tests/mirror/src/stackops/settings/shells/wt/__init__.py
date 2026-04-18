from pathlib import Path
from types import ModuleType

import stackops.settings.shells.wt as wt


def _module_path(module: ModuleType) -> Path:
    module_file = module.__file__
    assert module_file is not None
    return Path(module_file).resolve()


def test_wt_path_reference_points_to_shipped_settings() -> None:
    settings_path = _module_path(wt).parent / wt.SETTINGS_PATH_REFERENCE

    assert settings_path.is_file()
    assert settings_path.read_text(encoding="utf-8").strip()
