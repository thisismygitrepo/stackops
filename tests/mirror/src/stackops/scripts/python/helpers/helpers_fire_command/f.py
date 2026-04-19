

import importlib
from pathlib import Path


def test_f_module_is_empty_but_importable() -> None:
    module = importlib.import_module("stackops.scripts.python.helpers.helpers_fire_command.f")
    module_path = Path(module.__file__).resolve()
    public_names = {name for name in vars(module) if not name.startswith("__")}

    assert module_path.is_file()
    assert public_names == set()
