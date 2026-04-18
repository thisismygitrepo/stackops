from __future__ import annotations

from stackops.scripts.python.helpers.helpers_cloud.helpers5 import get_jupyter_notebook


def test_get_jupyter_notebook_inserts_requested_python_code() -> None:
    notebook = get_jupyter_notebook("print(42)")

    assert "print(42)" in notebook
    assert '"import math"' not in notebook
