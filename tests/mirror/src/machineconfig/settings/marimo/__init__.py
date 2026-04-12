from importlib.resources import files

import machineconfig.settings.marimo as marimo_settings


def test_marimo_path_reference_exists() -> None:
    assert (files(marimo_settings) / marimo_settings.MARIMO_PATH_REFERENCE).is_file()
