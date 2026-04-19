

import importlib


def test_options_utils_package_imports() -> None:
    module = importlib.import_module("stackops.utils.options_utils")

    assert module.__name__ == "stackops.utils.options_utils"
