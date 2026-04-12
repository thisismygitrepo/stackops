from __future__ import annotations

import importlib
from pathlib import Path


def test_template_references_point_to_existing_files() -> None:
    module = importlib.import_module("machineconfig.scripts.python.helpers.helpers_agents.templates")
    package_dir = Path(module.__file__ or "").parent

    assert package_dir.joinpath(module.PROMPT_PATH_REFERENCE).is_file()
    assert package_dir.joinpath(module.TEMPLATE_PS1_PATH_REFERENCE).is_file()
    assert package_dir.joinpath(module.TEMPLATE_SH_PATH_REFERENCE).is_file()
