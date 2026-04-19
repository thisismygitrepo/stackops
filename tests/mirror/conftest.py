

from pathlib import Path

import pytest


MIRROR_ROOT = Path(__file__).resolve().parent


def pytest_collect_file(file_path: Path, parent: pytest.Collector) -> pytest.Module | None:
    if file_path.name == "conftest.py" or file_path.suffix != ".py":
        return None
    try:
        file_path.relative_to(MIRROR_ROOT)
    except ValueError:
        return None
    return pytest.Module.from_parent(parent=parent, path=file_path)
