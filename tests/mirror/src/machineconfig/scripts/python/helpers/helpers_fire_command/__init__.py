from __future__ import annotations

import importlib
from pathlib import Path


def test_helpers_fire_command_package_imports() -> None:
    module = importlib.import_module("machineconfig.scripts.python.helpers.helpers_fire_command")
    module_path = Path(module.__file__).resolve()

    assert module_path.name == "__init__.py"
    assert module_path.is_file()
