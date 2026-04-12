from importlib.resources import files

import machineconfig.settings.pistol as pistol_settings


def test_pistol_path_reference_exists() -> None:
    assert (files(pistol_settings) / pistol_settings.PISTOL_PATH_REFERENCE).is_file()
