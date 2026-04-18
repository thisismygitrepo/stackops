from importlib.resources import files

import stackops.settings.pudb as pudb_settings


def test_pudb_path_reference_exists() -> None:
    assert (files(pudb_settings) / pudb_settings.PUDB_PATH_REFERENCE).is_file()
