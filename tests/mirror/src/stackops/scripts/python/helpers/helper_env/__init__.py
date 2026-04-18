from __future__ import annotations

import importlib


def test_module_exposes_expected_value() -> None:
    module = importlib.import_module("stackops.scripts.python.helpers.helper_env")

    assert getattr(module, "a") == 2
