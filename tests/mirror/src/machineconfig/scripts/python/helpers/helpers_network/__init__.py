import importlib.util
from pathlib import Path

_SOURCE_FILE = Path(__file__).resolve().parents[8] / "src/machineconfig/scripts/python/helpers/helpers_network/__init__.py"



def test_source_module_loads_without_public_exports() -> None:
    spec = importlib.util.spec_from_file_location("helpers_network_source", _SOURCE_FILE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    public_names = sorted(name for name in vars(module) if not name.startswith("_"))

    assert public_names == []
