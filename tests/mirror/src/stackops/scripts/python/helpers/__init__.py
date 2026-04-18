from __future__ import annotations

import importlib
from pathlib import Path


def test_package_imports() -> None:
    module = importlib.import_module("stackops.scripts.python.helpers")
    module_file = module.__file__

    assert module_file is not None
    assert Path(module_file).name == "__init__.py"
