from __future__ import annotations

import importlib


def test_options_utils_package_imports() -> None:
    module = importlib.import_module("machineconfig.utils.options_utils")

    assert module.__name__ == "machineconfig.utils.options_utils"
