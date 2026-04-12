from importlib import import_module
from pathlib import Path
from types import ModuleType


def _module_path(module: ModuleType) -> Path:
    module_file = module.__file__
    assert module_file is not None
    return Path(module_file).resolve()


def test_default_profile_package_ships_startup_subpackage() -> None:
    module = import_module("machineconfig.settings.shells.ipy.profiles.default")
    startup_dir = _module_path(module).parent / "startup"

    assert startup_dir.is_dir()
    assert (startup_dir / "__init__.py").is_file()
