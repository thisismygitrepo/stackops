import importlib


def test_python_scripts_package_imports_cleanly() -> None:
    module = importlib.import_module("machineconfig.scripts.python")
    assert module.__name__ == "machineconfig.scripts.python"
    assert hasattr(module, "__path__")
