from pathlib import Path

import stackops.scripts.python.graph.visualize as target


def test_visualize_package_init_exists() -> None:
    module_file_text = target.__file__

    assert module_file_text is not None
    module_file = Path(module_file_text)
    assert module_file.name == "__init__.py"
    assert module_file.exists()
