import importlib


MODULE_NAME = "machineconfig.scripts.python.helpers.helpers_devops"


def test_helpers_devops_package_imports_as_package() -> None:
    module = importlib.import_module(MODULE_NAME)

    assert module.__name__ == MODULE_NAME
    assert hasattr(module, "__path__")
    assert str(module.__file__).endswith("__init__.py")
