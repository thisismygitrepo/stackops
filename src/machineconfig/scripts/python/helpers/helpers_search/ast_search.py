
import ast
import os
from pathlib import Path
from typing import TypedDict


class SymbolInfo(TypedDict):
    """Represents a symbol (module, class, or function) in the repository."""
    type: str
    name: str
    path: str
    # line: int | None
    # column: int | None
    docstring: str


def _get_docstring(node: ast.AsyncFunctionDef | ast.FunctionDef | ast.ClassDef | ast.Module) -> str:
    """Extract docstring from an AST node."""
    return ast.get_docstring(node) or ""


def _extract_symbols(tree: ast.AST, module_path: str, source: str) -> list[SymbolInfo]:
    """Extract symbols from an AST tree."""
    symbols: list[SymbolInfo] = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            function_symbol: SymbolInfo = {
                "type": "function",
                "name": node.name,
                "path": f"{module_path}.{node.name}",
                "docstring": _get_docstring(node),
            }
            symbols.append(function_symbol)
        elif isinstance(node, ast.ClassDef):
            class_symbol: SymbolInfo = {
                "type": "class",
                "name": node.name,
                "path": f"{module_path}.{node.name}",
                "docstring": _get_docstring(node),
            }
            symbols.append(class_symbol)
    
    return symbols


def get_repo_symbols(repo_path: str) -> list[SymbolInfo]:
    skip_dirs = {'.venv', 'venv', '__pycache__', '.mypy_cache', '.pytest_cache', '.git'}
    results: list[SymbolInfo] = []
    counter: int = 0
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
        for file in files:
            if not file.endswith(".py"):
                continue
            file_path = os.path.join(root, file)
            module_path = (
                os.path.relpath(file_path, repo_path)
                .replace(os.sep, ".")
                .removesuffix(".py")
            )
            try:
                if counter % 100 == 0: print(f"🔍 Parsing {counter}: {file_path}...")
                source = Path(file_path).read_text(encoding="utf-8")
                tree = ast.parse(source, filename=file_path)
                symbols = _extract_symbols(tree, module_path, source)
                results.extend(symbols)
            except Exception as e:
                print(f"⚠️ Error parsing {file_path}: {e}")
                continue
            counter += 1

    return results
