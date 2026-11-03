import json
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

from stackops.scripts.python.helpers.helpers_seek.semantic.backend_names import SemanticBackend
from stackops.scripts.python.helpers.helpers_seek.semantic.constants import SEMANTIC_TOP_K
from stackops.scripts.python.helpers.helpers_seek.semantic.hit_selection import limit_distinct_hits
from stackops.scripts.python.helpers.helpers_seek.semantic.run_semantic_search import required_tools, search_with_backend
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticFailure


def run_semantic_json_search(
    path: str, query: str, extension: str | None, max_files: int, backend: SemanticBackend
) -> SemanticFailure | None:
    if query.strip() == "":
        return SemanticFailure(backend=backend, stage="options", message="Pass a search term when using --semantic --json")
    root = Path(path).resolve()
    if backend != "semtools" and root.is_file():
        return SemanticFailure(backend=backend, stage="options", message=f"""{backend} indexes directories; pass a directory instead of {root}""")
    missing_tools = [tool for tool in required_tools(backend=backend) if shutil.which(tool) is None]
    if missing_tools:
        return SemanticFailure(
            backend=backend,
            stage="install",
            message=f"""Missing tools: {", ".join(missing_tools)}. Run seek --install-dependencies -b {backend}""",
        )
    with redirect_stdout(sys.stderr):
        outcome = search_with_backend(backend=backend, root=root, query=query, extension=extension, max_files=max_files)
    if isinstance(outcome, SemanticFailure):
        return outcome
    hits = limit_distinct_hits(hits=outcome.hits, limit=SEMANTIC_TOP_K)
    records: list[dict[str, str | int | float]] = [
        {
            "path": str(hit.path),
            "start_line": hit.start_line,
            "end_line": hit.end_line,
            "focus_line": hit.focus_line,
            "metric": hit.metric,
            "value": hit.value,
            "content": hit.content,
        }
        for hit in hits
    ]
    print(json.dumps(records, ensure_ascii=False))
    return None
