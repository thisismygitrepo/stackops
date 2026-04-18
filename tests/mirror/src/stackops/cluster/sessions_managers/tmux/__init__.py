import importlib


def test_tmux_package_imports() -> None:
    module = importlib.import_module("stackops.cluster.sessions_managers.tmux")

    assert module.__name__ == "stackops.cluster.sessions_managers.tmux"
