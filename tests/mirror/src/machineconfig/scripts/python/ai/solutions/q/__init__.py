from __future__ import annotations

from pathlib import Path

import machineconfig.scripts.python.ai.solutions.q as q_assets


def test_q_package_imports_from_existing_module_file() -> None:
    assert q_assets.__file__ is not None
    assert Path(q_assets.__file__).is_file()
