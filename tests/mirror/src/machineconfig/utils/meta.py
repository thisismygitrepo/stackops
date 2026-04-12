from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.scripts.python.helpers.helpers_fire_command import file_wrangler
from machineconfig.utils import accessories
from machineconfig.utils import meta as meta_module


def _script_target(value: int, label: str = "fallback") -> str:
    message = f"{label}:{value}"
    return message


def test_get_import_module_string_includes_repo_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        file_wrangler,
        "get_import_module_code",
        lambda _py_file: "from package.sample import sample",
    )
    monkeypatch.setattr(accessories, "get_repo_root", lambda _path: Path("/repo"))

    script = meta_module.get_import_module_string("/repo/package/sample.py")

    assert "from package.sample import sample" in script
    assert "sys.path.append(r'/repo')" in script
    assert "from sample import *" in script


def test_lambda_to_python_script_inlines_closure_values() -> None:
    chosen_value = 7

    script = meta_module.lambda_to_python_script(
        lambda: _script_target(value=chosen_value, label="picked"),
        in_global=False,
        import_module=False,
    )

    assert "def _script_target" in script
    assert "value: 'int' = 7" in script
    assert "label: 'str' = 'picked'" in script
    assert "return message" in script


def test_lambda_to_python_script_global_mode_comments_trailing_return() -> None:
    script = meta_module.lambda_to_python_script(
        lambda: _script_target(value=3),
        in_global=True,
        import_module=False,
    )

    assert "def _script_target" not in script
    assert "value" in script
    assert "3" in script
    assert "# return message" in script
