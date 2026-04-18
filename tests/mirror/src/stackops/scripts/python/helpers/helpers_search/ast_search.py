from __future__ import annotations

from pathlib import Path

from stackops.scripts.python.helpers.helpers_search import ast_search as ast_search_module


def test_iter_python_files_skips_hidden_and_cache_directories(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "nested.py").write_text("y = 2\n", encoding="utf-8")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "skip.py").write_text("z = 3\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "skip.py").write_text("z = 4\n", encoding="utf-8")

    result = ast_search_module._iter_python_files(search_path=tmp_path)

    assert result == [tmp_path / "keep.py", tmp_path / "pkg" / "nested.py"]


def test_get_repo_symbols_extracts_nested_symbol_metadata(tmp_path: Path) -> None:
    package_dir = tmp_path / "pkg"
    package_dir.mkdir()
    source_path = package_dir / "mod.py"
    source_path.write_text(
        '''class Outer:\n    """outer doc"""\n\n    def method(self) -> int:\n        """method doc"""\n        def inner() -> int:\n            return 1\n        return inner()\n\n\nasync def coro() -> None:\n    """async doc"""\n    return None\n''',
        encoding="utf-8",
    )
    (package_dir / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    symbols = ast_search_module.get_repo_symbols(str(tmp_path))
    symbol_map = {symbol["path"]: symbol for symbol in symbols}

    assert set(symbol_map) == {"pkg.mod.Outer", "pkg.mod.Outer.method", "pkg.mod.Outer.method.inner", "pkg.mod.coro"}
    assert symbol_map["pkg.mod.Outer"]["docstring"] == "outer doc"
    assert symbol_map["pkg.mod.Outer.method"]["line"] == 4
    assert symbol_map["pkg.mod.Outer.method.inner"]["body"].startswith("def inner()")
    assert symbol_map["pkg.mod.coro"]["type"] == "async function"


def test_get_repo_symbols_handles_single_file_search_path(tmp_path: Path) -> None:
    source_path = tmp_path / "single.py"
    source_path.write_text("def work() -> int:\n    return 1\n", encoding="utf-8")

    symbols = ast_search_module.get_repo_symbols(str(source_path))

    assert len(symbols) == 1
    assert symbols[0]["file_path"] == "single.py"
    assert symbols[0]["path"] == "single.work"
