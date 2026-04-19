

import importlib.resources as resources

from stackops.utils.files import ouch


def test_ouch_package_contains_decompress_module() -> None:
    package_root = resources.files(ouch)

    assert package_root.joinpath("__init__.py").is_file()
    assert package_root.joinpath("decompress.py").is_file()
