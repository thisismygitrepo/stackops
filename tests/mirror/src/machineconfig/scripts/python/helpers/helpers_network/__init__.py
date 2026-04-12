import importlib

_MODULE_NAME = "machineconfig.scripts.python.helpers.helpers_network"



def test_module_imports_without_public_exports() -> None:
    module = importlib.import_module(_MODULE_NAME)
    public_names = sorted(name for name in vars(module) if not name.startswith("_"))

    assert public_names == []
