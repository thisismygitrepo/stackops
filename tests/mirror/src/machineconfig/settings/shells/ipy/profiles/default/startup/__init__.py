from importlib import import_module
from pathlib import Path
from types import ModuleType


def _module_path(module: ModuleType) -> Path:
    module_file = module.__file__
    assert module_file is not None
    return Path(module_file).resolve()


def test_startup_package_ships_playext_module() -> None:
    module = import_module("machineconfig.settings.shells.ipy.profiles.default.startup")
    playext_path = _module_path(module).parent / "playext.py"

    assert playext_path.is_file()
    assert playext_path.read_text(encoding="utf-8").strip()
