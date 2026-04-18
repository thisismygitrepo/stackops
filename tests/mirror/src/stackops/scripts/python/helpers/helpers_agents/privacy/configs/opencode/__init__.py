import importlib


MODULE_NAME = "stackops.scripts.python.helpers.helpers_agents.privacy.configs.opencode"


def test_opencode_package_imports() -> None:
    module = importlib.import_module(MODULE_NAME)
    assert module.__name__ == MODULE_NAME
