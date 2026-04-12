import importlib


def test_viewer_module_imports_without_exposing_runtime_api() -> None:
    module = importlib.import_module("machineconfig.scripts.python.helpers.helpers_croshell.viewer")

    assert hasattr(module, "__file__")
    assert not hasattr(module, "run")
    assert not hasattr(module, "default_get_figure")
