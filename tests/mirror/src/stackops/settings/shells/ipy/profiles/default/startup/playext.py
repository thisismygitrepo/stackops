from importlib import import_module
from pathlib import Path
from types import ModuleType


def _module_path(module: ModuleType) -> Path:
    module_file = module.__file__
    assert module_file is not None
    return Path(module_file).resolve()


def test_playext_module_is_importable_and_non_empty() -> None:
    module = import_module("stackops.settings.shells.ipy.profiles.default.startup.playext")
    module_path = _module_path(module)

    assert module_path.is_file()
    assert module_path.read_text(encoding="utf-8").strip()
