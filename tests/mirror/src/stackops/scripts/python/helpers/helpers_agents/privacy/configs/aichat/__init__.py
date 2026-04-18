from __future__ import annotations

import importlib
from pathlib import Path


def test_config_path_reference_points_to_existing_package_asset() -> None:
    module = importlib.import_module(
        "stackops.scripts.python.helpers.helpers_agents.privacy.configs.aichat"
    )

    assert module.__file__ is not None
    config_path = Path(module.__file__).resolve().parent / module.CONFIG_PATH_REFERENCE

    assert config_path.is_file()
    assert config_path.read_text(encoding="utf-8").strip() != ""
