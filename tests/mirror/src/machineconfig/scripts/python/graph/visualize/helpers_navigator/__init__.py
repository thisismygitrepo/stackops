from __future__ import annotations

from pathlib import Path

import machineconfig.scripts.python.graph.visualize.helpers_navigator as helpers_navigator


def test_helpers_navigator_package_imports() -> None:
    package_file = Path(helpers_navigator.__file__ or "")

    assert package_file.name == "__init__.py"
    assert package_file.is_file()
    assert list(helpers_navigator.__path__)
