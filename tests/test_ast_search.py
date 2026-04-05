from pathlib import Path
import textwrap

from machineconfig.scripts.python.helpers.helpers_search.ast_search import get_repo_symbols


def test_get_repo_symbols_captures_nested_symbol_paths_and_bodies(tmp_path: Path) -> None:
    source = textwrap.dedent(
        """
        class Outer:
            def method(self) -> int:
                return 1


        async def top() -> None:
            def nested() -> None:
                return None

            return None
        """
    ).lstrip()
    tmp_path.joinpath("demo.py").write_text(source, encoding="utf-8")

    symbols = get_repo_symbols(str(tmp_path))
    symbols_by_path = {symbol["path"]: symbol for symbol in symbols}

    outer_symbol = symbols_by_path["demo.Outer"]
    assert outer_symbol["type"] == "class"
    assert outer_symbol["file_path"] == "demo.py"
    assert outer_symbol["body"].startswith("class Outer:")

    method_symbol = symbols_by_path["demo.Outer.method"]
    assert method_symbol["type"] == "function"
    assert "def method(self) -> int:" in method_symbol["body"]

    top_symbol = symbols_by_path["demo.top"]
    assert top_symbol["type"] == "async function"
    assert top_symbol["body"].startswith("async def top() -> None:")

    nested_symbol = symbols_by_path["demo.top.nested"]
    assert nested_symbol["type"] == "function"
    assert "def nested() -> None:" in nested_symbol["body"]
