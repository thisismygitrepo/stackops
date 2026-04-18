from importlib import import_module
from pathlib import Path


def test_import_helpers_agents_package() -> None:
    module = import_module("stackops.scripts.python.helpers.helpers_agents")
    module_file = module.__file__
    assert module_file is not None
    assert Path(module_file).name == "__init__.py"
