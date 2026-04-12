from __future__ import annotations

import importlib


def test_package_import_exposes_package_path() -> None:
    module = importlib.import_module("machineconfig.cluster.sessions_managers.zellij")

    assert module.__package__ == "machineconfig.cluster.sessions_managers.zellij"
    assert getattr(module, "__path__", None) is not None
