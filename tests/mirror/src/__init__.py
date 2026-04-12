import importlib.util
from pathlib import Path
from typing import cast


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_INIT = REPO_ROOT / "src" / "__init__.py"


def test_src_package_file_can_be_loaded_as_package() -> None:
    spec = importlib.util.spec_from_file_location("src_under_test", SOURCE_INIT, submodule_search_locations=[str(SOURCE_INIT.parent)])

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module_file = Path(cast(str, module.__file__)).resolve()
    module_spec = module.__spec__

    assert module_file == SOURCE_INIT
    assert module_spec is not None
    assert module_spec.submodule_search_locations is not None
