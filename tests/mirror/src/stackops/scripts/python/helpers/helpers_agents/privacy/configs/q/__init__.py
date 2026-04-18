import importlib


MODULE_NAME = "stackops.scripts.python.helpers.helpers_agents.privacy.configs.q"


def test_q_package_imports() -> None:
    module = importlib.import_module(MODULE_NAME)
    assert module.__name__ == MODULE_NAME
