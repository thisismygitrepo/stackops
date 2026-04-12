import importlib


def test_helpers_devops_package_import_is_lazy() -> None:
    module = importlib.import_module("machineconfig.scripts.python.helpers.helpers_devops")

    assert hasattr(module, "__path__")
    assert not hasattr(module, "cli_config")
    assert not hasattr(module, "cli_data")
