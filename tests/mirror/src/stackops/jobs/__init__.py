from __future__ import annotations

import importlib


def test_jobs_package_imports() -> None:
    module = importlib.import_module("stackops.jobs")
    assert list(module.__path__)
