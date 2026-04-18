from pathlib import Path
from types import ModuleType

import stackops.settings.shells.nushell as nushell
import pytest


def _module_path(module: ModuleType) -> Path:
    module_file = module.__file__
    assert module_file is not None
    return Path(module_file).resolve()


def _referenced_paths() -> tuple[tuple[str, Path], tuple[str, Path], tuple[str, Path]]:
    module_dir = _module_path(nushell).parent
    return (
        ("CONFIG_PATH_REFERENCE", module_dir / nushell.CONFIG_PATH_REFERENCE),
        ("ENV_PATH_REFERENCE", module_dir / nushell.ENV_PATH_REFERENCE),
        ("INIT_PATH_REFERENCE", module_dir / nushell.INIT_PATH_REFERENCE),
    )


@pytest.mark.parametrize(("reference_name", "referenced_path"), _referenced_paths())
def test_nushell_path_references_point_to_shipped_files(reference_name: str, referenced_path: Path) -> None:
    assert referenced_path.is_file(), reference_name
    assert referenced_path.read_text(encoding="utf-8").strip(), reference_name
