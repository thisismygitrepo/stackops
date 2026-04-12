import importlib


def test_tmux_package_imports() -> None:
    module = importlib.import_module("machineconfig.cluster.sessions_managers.tmux")

    assert module.__name__ == "machineconfig.cluster.sessions_managers.tmux"
