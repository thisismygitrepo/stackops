

import importlib


def test_package_imports() -> None:
    module = importlib.import_module("stackops.scripts.python.helpers.helpers_devops.cli_self_ai")

    assert module.__package__ == "stackops.scripts.python.helpers.helpers_devops.cli_self_ai"
    assert hasattr(module, "__path__")
