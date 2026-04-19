

from pathlib import Path

import stackops.scripts.python.ai.solutions.droid as droid_assets


def test_package_is_importable_and_contains_runtime_entrypoint() -> None:
    package_path = Path(droid_assets.__file__).resolve()

    assert package_path.name == "__init__.py"
    assert package_path.is_file()
    assert package_path.parent.joinpath("droid.py").is_file()
