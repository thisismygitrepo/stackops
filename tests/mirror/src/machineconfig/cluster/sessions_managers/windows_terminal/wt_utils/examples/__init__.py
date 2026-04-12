from __future__ import annotations

import importlib
from pathlib import Path


def test_examples_package_imports() -> None:
    module = importlib.import_module("machineconfig.cluster.sessions_managers.windows_terminal.wt_utils.examples")

    assert Path(module.__file__ or "").name == "__init__.py"
