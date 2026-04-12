from __future__ import annotations

import importlib


def test_package_imports() -> None:
    module = importlib.import_module("machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai")

    assert module.__package__ == "machineconfig.scripts.python.helpers.helpers_devops.cli_self_ai"
    assert hasattr(module, "__path__")
