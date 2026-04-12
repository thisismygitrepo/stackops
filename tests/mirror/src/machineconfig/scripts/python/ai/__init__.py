import importlib


def test_ai_package_imports_cleanly() -> None:
    module = importlib.import_module("machineconfig.scripts.python.ai")
    assert module.__name__ == "machineconfig.scripts.python.ai"
    assert hasattr(module, "__path__")
