import base64
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_search.ast_search import SymbolInfo, get_repo_symbols
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_names import SemanticBackend
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticFailure


class RipgrepText(TypedDict, total=False):
    text: str
    bytes: str


class RipgrepSubmatch(TypedDict):
    start: int


class RipgrepMatch(TypedDict):
    path: RipgrepText
    lines: RipgrepText
    line_number: int
    submatches: list[RipgrepSubmatch]


class RipgrepEvent(TypedDict):
    type: str
    data: RipgrepMatch


class TextHit(TypedDict):
    path: str
    line: int
    column: int
    text: str


class FileHit(TypedDict):
    path: str


def _filter_candidates(candidates: list[str], query: str) -> list[str]:
    if query == "" or not candidates:
        return candidates
    completed = subprocess.run(
        ["fzf", "--read0", "--print0", "--filter", query],
        input="\0".join(candidates) + "\0",
        capture_output=True,
        encoding="utf-8",
        env={key: value for key, value in os.environ.items() if key not in {"FZF_DEFAULT_OPTS", "FZF_DEFAULT_OPTS_FILE"}},
        check=False,
    )
    if completed.returncode not in (0, 1):
        completed.check_returncode()
    return [candidate for candidate in completed.stdout.split("\0") if candidate != ""]


def _decode_ripgrep_text(value: RipgrepText) -> str:
    if "text" in value:
        return value["text"]
    assert "bytes" in value
    return base64.b64decode(value["bytes"]).decode("utf-8", errors="replace")


def _search_text(root: Path, query: str, extension: str | None, dotfiles: bool, rga: bool) -> list[TextHit]:
    command = ["rga" if rga else "rg", "--no-config", "--json", "--color", "never", "--smart-case", "--sort", "path"]
    if dotfiles:
        command.append("--hidden")
    if extension is not None:
        command.extend(["--glob", f"""*.{extension.lstrip('.')}"""])
    command.extend(["--", query, str(root)])
    completed = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", check=False)
    if completed.returncode not in (0, 1):
        completed.check_returncode()
    if completed.stderr:
        print(completed.stderr, file=sys.stderr, end="")
    hits: list[TextHit] = []
    for line in completed.stdout.splitlines():
        event = cast(RipgrepEvent, json.loads(line))
        if event["type"] != "match":
            continue
        match = event["data"]
        hits.append(
            {
                "path": _decode_ripgrep_text(value=match["path"]),
                "line": match["line_number"],
                "column": match["submatches"][0]["start"] + 1,
                "text": _decode_ripgrep_text(value=match["lines"]).rstrip("\r\n"),
            }
        )
    return hits


def _search_files(root: Path, query: str, extension: str | None, dotfiles: bool) -> list[FileHit]:
    if root.is_file():
        candidates = [root.name] if extension is None or root.name.endswith(f""".{extension.lstrip('.')}""") else []
        directory = root.parent
    else:
        directory = root
        command = ["fd", "--type", "file", "--color", "never", "--print0"]
        if dotfiles:
            command.append("--hidden")
        if extension is not None:
            command.extend(["--extension", extension.lstrip(".")])
        command.extend([".", "."])
        completed = subprocess.run(command, cwd=root, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", check=True)
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        candidates = sorted(name for name in completed.stdout.split("\0") if name != "")
    selected = _filter_candidates(candidates=candidates, query=query)
    return [{"path": str(directory / name)} for name in selected]


def _search_symbols(root: Path, query: str, extension: str | None) -> list[SymbolInfo]:
    with redirect_stdout(sys.stderr):
        symbols = get_repo_symbols(search_path=str(root))
    directory = root.parent if root.is_file() else root
    lookup: dict[str, SymbolInfo] = {}
    for symbol in sorted(symbols, key=lambda item: (item["file_path"], item["line"])):
        if extension is not None and not symbol["file_path"].endswith(f""".{extension.lstrip('.')}"""):
            continue
        label = f"""{symbol['path']} [{symbol['file_path']}:{symbol['line']}]"""
        symbol["file_path"] = str(directory / symbol["file_path"])
        lookup[label] = symbol
    return [lookup[label] for label in _filter_candidates(candidates=list(lookup), query=query)]


def run_json_search(
    path: str,
    query: str,
    ast: bool,
    semantic: bool,
    semantic_backend: SemanticBackend,
    max_files: int,
    extension: str | None,
    file: bool,
    dotfiles: bool,
    rga: bool,
) -> SemanticFailure | None:
    if semantic:
        from stackops.scripts.python.helpers.helpers_seek.semantic.json_search import run_semantic_json_search

        return run_semantic_json_search(path=path, query=query, extension=extension, max_files=max_files, backend=semantic_backend)
    root = Path(path).resolve(strict=True)
    results: list[SymbolInfo] | list[FileHit] | list[TextHit]
    if ast:
        results = _search_symbols(root=root, query=query, extension=extension)
    elif file:
        results = _search_files(root=root, query=query, extension=extension, dotfiles=dotfiles)
    else:
        results = _search_text(root=root, query=query, extension=extension, dotfiles=dotfiles, rga=rga)
    print(json.dumps(results, ensure_ascii=False))
    return None
