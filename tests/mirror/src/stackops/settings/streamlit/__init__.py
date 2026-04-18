from pathlib import Path

from stackops.settings import streamlit


def _assert_local_reference(module_dir: Path, relative_path: str) -> None:
    reference_path = Path(relative_path)
    assert not reference_path.is_absolute()
    assert reference_path == Path(reference_path.name)
    assert (module_dir / reference_path).is_file()


def test_config_path_reference_points_to_existing_local_file() -> None:
    module_dir = Path(streamlit.__file__).resolve().parent
    _assert_local_reference(module_dir, streamlit.CONFIG_PATH_REFERENCE)
