

import importlib


def test_package_import_exposes_package_path() -> None:
    module = importlib.import_module("stackops.cluster.sessions_managers.zellij")

    assert module.__package__ == "stackops.cluster.sessions_managers.zellij"
    assert getattr(module, "__path__", None) is not None
