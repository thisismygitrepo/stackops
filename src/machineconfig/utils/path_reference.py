from pathlib import Path
from types import ModuleType

from machineconfig.utils.source_of_truth import LIBRARY_ROOT


def _get_module_file(module: ModuleType) -> Path:
    module_file = module.__file__
    if module_file is None:
        raise ValueError(f"Module does not define __file__: {module!r}")
    return Path(module_file).resolve()


def get_path_reference_path(module: ModuleType, path_reference: str) -> Path:
    return _get_module_file(module).parent.joinpath(path_reference).resolve()


def get_path_reference_library_relative_path(module: ModuleType, path_reference: str) -> Path:
    return get_path_reference_path(module=module, path_reference=path_reference).relative_to(LIBRARY_ROOT)
