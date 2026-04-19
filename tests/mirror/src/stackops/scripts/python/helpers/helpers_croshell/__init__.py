

import importlib


def test_module_imports_as_empty_namespace() -> None:
    module = importlib.import_module("stackops.scripts.python.helpers.helpers_croshell")

    assert module.__file__ is not None
    assert not hasattr(module, "croshell")
