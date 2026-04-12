from __future__ import annotations

import importlib


def test_repo_rag_module_has_no_runtime_api() -> None:
    module = importlib.import_module("machineconfig.scripts.python.helpers.helpers_search.repo_rag")
    public_names = [name for name in vars(module) if not name.startswith("__")]

    assert public_names == []
