from __future__ import annotations

from pathlib import Path

import machineconfig.scripts.python.ai.solutions.qwen_code as qwen_code_assets


def test_qwen_code_package_imports_from_existing_module_file() -> None:
    assert qwen_code_assets.__file__ is not None
    assert Path(qwen_code_assets.__file__).is_file()
