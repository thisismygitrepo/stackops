

import importlib


def test_symantic_search_module_docstring_keeps_cli_requirements() -> None:
    module = importlib.import_module("stackops.scripts.python.helpers.helpers_search.symantic_search")

    assert module.__doc__ is not None
    assert "create-index" in module.__doc__
    assert "MEILI_URL" in module.__doc__
    assert "MEILI_MASTER_KEY" in module.__doc__
