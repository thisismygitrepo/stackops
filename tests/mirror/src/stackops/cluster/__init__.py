from importlib import import_module
from pathlib import Path
from typing import cast


REPO_ROOT = Path(__file__).resolve().parents[5]


def test_stackops_cluster_is_importable_package() -> None:
    module = import_module("stackops.cluster")
    module_file = Path(cast(str, module.__file__)).resolve()
    spec = module.__spec__

    assert module_file == REPO_ROOT / "src" / "stackops" / "cluster" / "__init__.py"
    assert spec is not None
    assert spec.submodule_search_locations is not None
