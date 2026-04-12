from __future__ import annotations

from pathlib import Path

import machineconfig.settings as module


def test_settings_module_imports_cleanly() -> None:
    assert module.__spec__ is not None
    assert module.__file__ is not None
    module_path = Path(module.__file__)
    assert module_path.name == "__init__.py"
    assert module_path.parent.name == "settings"
