

import importlib
from pathlib import Path


def test_auggie_package_import_exposes_expected_package_directory() -> None:
    package = importlib.import_module(
        "stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie"
    )
    privacy_module = importlib.import_module(
        "stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie.auggie_privacy"
    )

    assert package.__file__ is not None
    init_path = Path(package.__file__).resolve()

    assert init_path.name == "__init__.py"
    assert init_path.parent.name == "auggie"
    assert callable(privacy_module.secure_auggie_config)
