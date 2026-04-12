from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest

import machineconfig.utils.path_reference as path_reference


def test_get_module_file_requires_non_null_dunder_file() -> None:
    module = ModuleType("demo")
    setattr(module, "__file__", None)

    with pytest.raises(ValueError):
        path_reference._get_module_file(module)


def test_path_reference_helpers_resolve_against_module_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    library_root = tmp_path.joinpath("library")
    module_dir = library_root.joinpath("pkg")
    module_dir.mkdir(parents=True)
    module_file = module_dir.joinpath("module.py")
    module_file.write_text("", encoding="utf-8")

    module = ModuleType("pkg.module")
    setattr(module, "__file__", module_file.as_posix())
    monkeypatch.setattr(path_reference, "LIBRARY_ROOT", library_root)

    resolved = path_reference.get_path_reference_path(module, "../assets/config.toml")
    relative = path_reference.get_path_reference_library_relative_path(module, "../assets/config.toml")

    assert resolved == library_root.joinpath("assets", "config.toml").resolve()
    assert relative == Path("assets/config.toml")
