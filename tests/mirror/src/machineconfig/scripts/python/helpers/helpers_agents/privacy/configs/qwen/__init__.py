from __future__ import annotations

import importlib
from pathlib import Path


def test_qwen_package_contains_privacy_module() -> None:
    module = importlib.import_module(
        "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.qwen"
    )
    package_init = Path(module.__file__ or "")

    assert package_init.name == "__init__.py"
    assert package_init.parent.joinpath("qwen_privacy.py").is_file()
