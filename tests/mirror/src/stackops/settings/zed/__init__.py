from __future__ import annotations

from pathlib import Path

from stackops.settings import zed


def test_zed_settings_path_reference_points_to_existing_file() -> None:
    module_dir = Path(zed.__file__).resolve().parent
    resolved_path = module_dir.joinpath(zed.SETTINGS_PATH_REFERENCE)

    assert resolved_path.is_file()
