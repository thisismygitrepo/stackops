from importlib import import_module


def test_mount_helpers_package_imports() -> None:
    module = import_module("stackops.scripts.python.helpers.helpers_devops.mount_helpers")

    assert module.__file__ is not None
