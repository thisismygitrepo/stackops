import ast
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, TypedDict


type SymbolType = Literal["async function", "class", "function"]


class SymbolInfo(TypedDict):
    type: SymbolType
    name: str
    path: str
    file_path: str
    line: int
    end_line: int
    docstring: str
    body: str


def _get_docstring(node: ast.AsyncFunctionDef | ast.FunctionDef | ast.ClassDef | ast.Module) -> str:
    return ast.get_docstring(node) or ""


def _build_symbol_body(node: ast.AsyncFunctionDef | ast.ClassDef | ast.FunctionDef, source: str, source_lines: Sequence[str]) -> str:
    body = ast.get_source_segment(source, node)
    if body is not None:
        return body
    end_line = _require_end_line(node=node)
    return "".join(source_lines[node.lineno - 1 : end_line]).rstrip("\n")


def _build_symbol_path(module_path: str, parents: tuple[str, ...], symbol_name: str) -> str:
    parts = [module_path, *parents, symbol_name]
    return ".".join(part for part in parts if part != "")


def _build_symbol_type(node: ast.AsyncFunctionDef | ast.ClassDef | ast.FunctionDef) -> SymbolType:
    match node:
        case ast.AsyncFunctionDef():
            return "async function"
        case ast.ClassDef():
            return "class"
        case ast.FunctionDef():
            return "function"


def _require_end_line(node: ast.AsyncFunctionDef | ast.ClassDef | ast.FunctionDef) -> int:
    end_line = node.end_lineno
    if end_line is None:
        raise ValueError(f"""Missing end line information for symbol "{node.name}".""")
    return end_line


def _extract_symbols_from_body(
    body: Sequence[ast.stmt], module_path: str, relative_file_path: str, source: str, source_lines: Sequence[str], parents: tuple[str, ...]
) -> list[SymbolInfo]:
    symbols: list[SymbolInfo] = []
    for node in body:
        if not isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        symbol: SymbolInfo = {
            "type": _build_symbol_type(node),
            "name": node.name,
            "path": _build_symbol_path(module_path=module_path, parents=parents, symbol_name=node.name),
            "file_path": relative_file_path,
            "line": node.lineno,
            "end_line": _require_end_line(node=node),
            "docstring": _get_docstring(node),
            "body": _build_symbol_body(node=node, source=source, source_lines=source_lines),
        }
        symbols.append(symbol)
        symbols.extend(
            _extract_symbols_from_body(
                body=node.body,
                module_path=module_path,
                relative_file_path=relative_file_path,
                source=source,
                source_lines=source_lines,
                parents=(*parents, node.name),
            )
        )
    return symbols


def _iter_python_files(search_path: Path) -> list[Path]:
    skip_dirs = {".git", ".mypy_cache", ".pytest_cache", ".venv", "__pycache__", "venv"}
    if search_path.is_file():
        if search_path.suffix != ".py":
            return []
        return [search_path]

    python_files: list[Path] = []
    for root_path in search_path.rglob("*"):
        if not root_path.is_file() or root_path.suffix != ".py":
            continue
        if any(part in skip_dirs or part.startswith(".") for part in root_path.relative_to(search_path).parts[:-1]):
            continue
        python_files.append(root_path)
    return python_files


def _build_module_metadata(search_path: Path, root_path: Path) -> tuple[str, str]:
    if search_path.is_file():
        relative_file_path = root_path.name
    else:
        relative_file_path = root_path.relative_to(search_path).as_posix()
    module_path = relative_file_path.replace("/", ".").removesuffix(".py")
    return relative_file_path, module_path


def get_repo_symbols(search_path: str) -> list[SymbolInfo]:
    resolved_search_path = Path(search_path).resolve()
    results: list[SymbolInfo] = []
    counter: int = 0
    for root_path in _iter_python_files(search_path=resolved_search_path):
        relative_file_path, module_path = _build_module_metadata(search_path=resolved_search_path, root_path=root_path)
        try:
            if counter % 100 == 0:
                print(f"🔍 Parsing {counter}: {root_path}...")
            source = root_path.read_text(encoding="utf-8")
            source_lines = source.splitlines(keepends=True)
            tree = ast.parse(source, filename=str(root_path))
            results.extend(
                _extract_symbols_from_body(
                    body=tree.body,
                    module_path=module_path,
                    relative_file_path=relative_file_path,
                    source=source,
                    source_lines=source_lines,
                    parents=(),
                )
            )
        except Exception as exc:
            print(f"⚠️ Error parsing {root_path}: {exc}")
            continue
        counter += 1
    return results
