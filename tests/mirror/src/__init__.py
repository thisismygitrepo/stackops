from importlib import import_module
from pathlib import Path
from typing import cast


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_src_is_importable_package() -> None:
    module = import_module("src")
    module_file = Path(cast(str, module.__file__)).resolve()
    spec = module.__spec__

    assert module_file == REPO_ROOT / "src" / "__init__.py"
    assert spec is not None
    assert spec.submodule_search_locations is not None
