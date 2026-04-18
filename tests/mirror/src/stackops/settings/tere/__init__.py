from pathlib import Path

import pytest

from stackops.settings import tere

_PATH_REFERENCES: tuple[tuple[str, str], ...] = (
    ("TERECD_PS1_PATH_REFERENCE", tere.TERECD_PS1_PATH_REFERENCE),
    ("TERECD_SH_PATH_REFERENCE", tere.TERECD_SH_PATH_REFERENCE),
)


def _assert_local_reference(module_dir: Path, constant_name: str, relative_path: str) -> None:
    reference_path = Path(relative_path)
    assert not reference_path.is_absolute(), constant_name
    assert reference_path == Path(reference_path.name), constant_name
    assert (module_dir / reference_path).is_file(), constant_name


@pytest.mark.parametrize(("constant_name", "relative_path"), _PATH_REFERENCES)
def test_path_references_point_to_existing_local_files(constant_name: str, relative_path: str) -> None:
    module_dir = Path(tere.__file__).resolve().parent
    _assert_local_reference(module_dir, constant_name, relative_path)
