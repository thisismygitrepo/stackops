from __future__ import annotations

import importlib


def test_module_imports_without_cli_entrypoint() -> None:
    module = importlib.import_module("machineconfig.scripts.python.helpers.helpers_croshell.scheduler")

    assert module.__file__ is not None
    assert not hasattr(module, "main_parse")
