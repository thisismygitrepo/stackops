from __future__ import annotations

import importlib
from pathlib import Path


def test_cloud_manager_module_imports_without_public_api() -> None:
    module = importlib.import_module("machineconfig.scripts.python.helpers.helpers_fire_command.cloud_manager")
    module_path = Path(module.__file__).resolve()

    assert module_path.is_file()
    assert not hasattr(module, "main")
