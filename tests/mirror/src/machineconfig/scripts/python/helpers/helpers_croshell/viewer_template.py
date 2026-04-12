import importlib


def test_viewer_template_module_imports_as_comment_only_template() -> None:
    module = importlib.import_module(
        "machineconfig.scripts.python.helpers.helpers_croshell.viewer_template"
    )

    assert hasattr(module, "__file__")
    assert not hasattr(module, "change_index")
    assert not hasattr(module, "get_figure")
