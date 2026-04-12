from __future__ import annotations

import importlib
from pathlib import Path


def test_warp_package_imports_from_expected_directory() -> None:
    module = importlib.import_module("machineconfig.scripts.python.ai.solutions.warp")

    module_file = getattr(module, "__file__", None)

    assert isinstance(module_file, str)
    assert Path(module_file).name == "__init__.py"
    assert Path(module_file).parent.name == "warp"
