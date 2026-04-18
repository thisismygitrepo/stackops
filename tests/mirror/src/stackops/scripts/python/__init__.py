import importlib


def test_python_scripts_package_imports_cleanly() -> None:
    module = importlib.import_module("stackops.scripts.python")
    assert module.__name__ == "stackops.scripts.python"
    assert hasattr(module, "__path__")
