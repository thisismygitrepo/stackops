from importlib.resources import files

import stackops.settings.presenterm as presenterm_settings


def test_presenterm_path_reference_exists() -> None:
    assert (files(presenterm_settings) / presenterm_settings.CONFIG_PATH_REFERENCE).is_file()
