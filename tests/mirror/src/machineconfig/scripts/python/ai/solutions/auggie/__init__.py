from __future__ import annotations

from pathlib import Path

import machineconfig.scripts.python.ai.solutions.auggie as auggie_package


def test_auggie_package_imports_from_repository() -> None:
    assert auggie_package.__file__ is not None
    module_path = Path(auggie_package.__file__)

    assert module_path.name == "__init__.py"
    assert module_path.is_file()
