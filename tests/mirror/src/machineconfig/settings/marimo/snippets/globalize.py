import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import cast


def _get_object_attr(value: object, name: str) -> object:
    return cast(object, getattr(value, name))


def _get_str_attr(value: object, name: str) -> str:
    attr = getattr(value, name)
    assert isinstance(attr, str)
    return attr


def _load_globalize_module() -> ModuleType:
    shadow_parent = Path(__file__).resolve().parents[2]
    original_sys_path = sys.path[:]

    try:
        sys.path = [
            entry
            for entry in sys.path
            if Path(entry or ".").resolve() != shadow_parent
        ]
        sys.modules.pop("marimo", None)
        sys.modules.pop("machineconfig.settings.marimo.snippets.globalize", None)
        return importlib.import_module("machineconfig.settings.marimo.snippets.globalize")
    finally:
        sys.path = original_sys_path


def test_globalize_app_registers_expected_cells() -> None:
    globalize_module = _load_globalize_module()
    app = _get_object_attr(globalize_module, "app")
    config = _get_object_attr(app, "_config")
    cell_manager = _get_object_attr(app, "_cell_manager")
    cell_data = _get_object_attr(cell_manager, "_cell_data")

    assert _get_str_attr(config, "width") == "full"
    assert isinstance(cell_data, dict)

    codes = {_get_str_attr(cell, "code") for cell in cell_data.values()}

    assert len(cell_data) == 3
    assert 'mo.md(r"""# Globalize Lambda to Python Script""")' in codes
    assert "import marimo as mo" in codes
    assert any(
        "lambda_to_python_script" in code
        and "in_global=True" in code
        and "import_module=False" in code
        for code in codes
    )
