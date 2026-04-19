

from pathlib import Path

import stackops.utils.ai as target_module


def test_utils_ai_package_file_exists() -> None:
    module_file = target_module.__file__
    assert module_file is not None
    resolved_module_file = Path(module_file).resolve()

    assert resolved_module_file.name == "__init__.py"
    assert resolved_module_file.parent.is_dir()
