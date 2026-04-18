from __future__ import annotations

from pathlib import Path

import stackops.scripts.python.ai.solutions as solutions_module


def test_solutions_package_imports_from_repository() -> None:
    assert solutions_module.__file__ is not None
    module_path = Path(solutions_module.__file__)

    assert module_path.name == "__init__.py"
    assert module_path.is_file()
