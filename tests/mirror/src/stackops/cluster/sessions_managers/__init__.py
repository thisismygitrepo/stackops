from __future__ import annotations

import importlib
from types import ModuleType


def test_sessions_managers_package_imports() -> None:
    module = importlib.import_module("stackops.cluster.sessions_managers")

    assert isinstance(module, ModuleType)
    assert module.__name__ == "stackops.cluster.sessions_managers"
