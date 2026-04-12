import importlib


def test_windows_terminal_package_imports() -> None:
    module = importlib.import_module("machineconfig.cluster.sessions_managers.windows_terminal")

    assert module.__name__ == "machineconfig.cluster.sessions_managers.windows_terminal"
