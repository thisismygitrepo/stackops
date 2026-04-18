from __future__ import annotations

from pathlib import Path

from stackops.settings import zellij


def test_zellij_config_path_reference_points_to_existing_file() -> None:
    module_dir = Path(zellij.__file__).resolve().parent
    resolved_path = module_dir.joinpath(zellij.CONFIG_PATH_REFERENCE)

    assert resolved_path.is_file()
