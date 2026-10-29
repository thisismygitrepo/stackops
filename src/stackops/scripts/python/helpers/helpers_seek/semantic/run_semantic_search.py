from pathlib import Path
from typing import assert_never

from stackops.scripts.python.helpers.helpers_seek.semantic.backend_names import SemanticBackend
from stackops.scripts.python.helpers.helpers_seek.semantic.constants import SEMANTIC_TOP_K
from stackops.scripts.python.helpers.helpers_seek.semantic.hit_selection import choose_and_open_hit, limit_distinct_hits
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticFailure, SemanticOutcome


def required_tools(backend: SemanticBackend) -> tuple[str, ...]:
    match backend:
        case "semtools":
            return ("semtools", "rg")
        case "ck":
            return ("ck",)
        case "grepai":
            return ("grepai",)
        case "qmd":
            return ("qmd",)
        case _:
            assert_never(backend)


def ensure_semantic_tools(backend: SemanticBackend) -> SemanticFailure | None:
    from stackops.utils.installer_utils.installer_cli import install_if_missing

    for tool in required_tools(backend=backend):
        if not install_if_missing(which=tool, binary_name=None, verbose=True):
            return SemanticFailure(backend=backend, stage="install", message=f"""{tool} is not installed and could not be installed automatically""")
    return None


def search_with_backend(backend: SemanticBackend, root: Path, query: str, extension: str | None, max_files: int) -> SemanticOutcome:
    match backend:
        case "semtools":
            from stackops.scripts.python.helpers.helpers_seek.semantic.backend_semtools import search_semtools

            return search_semtools(root=root, query=query, extension=extension, max_files=max_files, top_k=SEMANTIC_TOP_K)
        case "ck":
            from stackops.scripts.python.helpers.helpers_seek.semantic.backend_ck import search_ck

            return search_ck(root=root, query=query, extension=extension, top_k=SEMANTIC_TOP_K)
        case "grepai":
            from stackops.scripts.python.helpers.helpers_seek.semantic.backend_grepai import search_grepai

            return search_grepai(root=root, query=query, extension=extension, top_k=SEMANTIC_TOP_K)
        case "qmd":
            from stackops.scripts.python.helpers.helpers_seek.semantic.backend_qmd import search_qmd

            return search_qmd(root=root, query=query, extension=extension, top_k=SEMANTIC_TOP_K)
        case _:
            assert_never(backend)


def run_semantic_search(
    path: str, query: str, extension: str | None, max_files: int, backend: SemanticBackend, edit: bool
) -> SemanticFailure | None:
    root = Path(path).resolve()
    if backend != "semtools" and root.is_file():
        return SemanticFailure(backend=backend, stage="options", message=f"""{backend} indexes directories; pass a directory instead of {root}""")
    tools_failure = ensure_semantic_tools(backend=backend)
    if tools_failure is not None:
        return tools_failure
    if query == "":
        query = input("Enter search term for semantic search: ")
    outcome = search_with_backend(backend=backend, root=root, query=query, extension=extension, max_files=max_files)
    if isinstance(outcome, SemanticFailure):
        return outcome
    hits = limit_distinct_hits(hits=outcome.hits, limit=SEMANTIC_TOP_K)
    if len(hits) == 0:
        print("❓ No semantic matches found.")
        return None
    choose_and_open_hit(hits=hits, edit=edit)
    return None
