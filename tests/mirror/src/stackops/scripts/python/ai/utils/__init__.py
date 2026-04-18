from __future__ import annotations

import importlib
from pathlib import Path


def test_ai_utils_package_imports_from_expected_directory() -> None:
    module = importlib.import_module("stackops.scripts.python.ai.utils")

    module_file = getattr(module, "__file__", None)

    assert isinstance(module_file, str)
    assert Path(module_file).name == "__init__.py"
    assert Path(module_file).parent.name == "utils"
