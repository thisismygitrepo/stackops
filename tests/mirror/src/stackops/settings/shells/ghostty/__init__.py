from importlib.resources import files

import stackops.settings.shells.ghostty as ghostty_settings


def test_ghostty_path_reference_exists() -> None:
    assert (files(ghostty_settings) / ghostty_settings.CONFIG_PATH_REFERENCE).is_file()
