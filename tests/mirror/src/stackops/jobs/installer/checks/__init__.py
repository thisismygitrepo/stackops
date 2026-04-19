

import importlib


def test_checks_package_imports() -> None:
    module = importlib.import_module("stackops.jobs.installer.checks")
    assert list(module.__path__)
