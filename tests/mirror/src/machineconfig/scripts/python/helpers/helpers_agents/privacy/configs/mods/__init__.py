import importlib


MODULE_NAME = "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.mods"


def test_mods_package_imports() -> None:
    module = importlib.import_module(MODULE_NAME)
    assert module.__name__ == MODULE_NAME
