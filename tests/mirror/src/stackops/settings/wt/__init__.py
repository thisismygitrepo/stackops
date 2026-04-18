from __future__ import annotations

import importlib
from pathlib import Path


def test_wt_package_is_importable() -> None:
    module = importlib.import_module("stackops.settings.wt")
    module_file = module.__file__

    assert module_file is not None
    assert Path(module_file).name == "__init__.py"
    assert module.__package__ == "stackops.settings.wt"
