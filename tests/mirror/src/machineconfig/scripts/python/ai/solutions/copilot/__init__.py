from __future__ import annotations

from pathlib import Path

import machineconfig.scripts.python.ai.solutions.copilot as copilot_package


def test_copilot_package_references_existing_privacy_file() -> None:
    assert copilot_package.__file__ is not None
    module_path = Path(copilot_package.__file__)
    referenced_path = module_path.with_name(copilot_package.PRIVACY_PATH_REFERENCE)

    assert referenced_path.is_file()
    assert referenced_path.stat().st_size > 0
