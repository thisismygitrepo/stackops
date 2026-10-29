import hashlib
import json
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_seek.semantic.command_runner import run_backend_command
from stackops.scripts.python.helpers.helpers_seek.semantic.constants import (
    IDENTIFIER_HASH_LENGTH,
    RG_NO_MATCH_EXIT_CODE,
    SEMTOOLS_CONTEXT_LINES,
    SEMTOOLS_OVERFETCH_FACTOR,
    SEMTOOLS_WORKSPACE_PREFIX,
)
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import (
    SemanticFailure,
    SemanticHit,
    SemanticOutcome,
    SemanticSuccess,
)


class SemtoolsRecord(TypedDict):
    filename: str
    start_line_number: int
    end_line_number: int
    match_line_number: int
    distance: float
    content: str


class SemtoolsResponse(TypedDict):
    results: list[SemtoolsRecord]


def parse_semtools_output(stdout: str) -> list[SemanticHit] | SemanticFailure:
    try:
        response = cast(SemtoolsResponse, json.loads(stdout))
        return [
            SemanticHit(
                path=Path(record["filename"]),
                start_line=record["start_line_number"] + 1,
                end_line=record["end_line_number"],
                focus_line=record["match_line_number"] + 1,
                metric="distance",
                value=record["distance"],
                content=record["content"],
            )
            for record in response["results"]
        ]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        return SemanticFailure(backend="semtools", stage="parse", message=f"""unexpected semtools output: {error!r}""")


def list_text_files(root: Path, extension: str | None) -> list[Path] | SemanticFailure:
    if root.is_file():
        return [root]
    glob_arguments = [] if extension is None else ["--glob", f"*{extension}"]
    stdout = run_backend_command(
        backend="semtools",
        stage="discover",
        command=["rg", "--files-with-matches", "--null", *glob_arguments, "--", "", str(root)],
        cwd=root,
        extra_env={},
        accepted_exit_codes=(0, RG_NO_MATCH_EXIT_CODE),
        capture_stdout=True,
    )
    if isinstance(stdout, SemanticFailure):
        return stdout
    return [Path(name) for name in stdout.split("\0") if name != ""]


def search_semtools(root: Path, query: str, extension: str | None, max_files: int, top_k: int) -> SemanticOutcome:
    files = list_text_files(root=root, extension=extension)
    if isinstance(files, SemanticFailure):
        return files
    if len(files) == 0:
        return SemanticFailure(backend="semtools", stage="discover", message=f"""no searchable text files under {root}""")
    if max_files != 0 and len(files) > max_files:
        return SemanticFailure(
            backend="semtools",
            stage="discover",
            message=f"""found {len(files)} text files, which exceeds --max-files {max_files}; raise it, pass 0 to disable the limit, or narrow the path or --extension""",
        )
    workspace = f"""{SEMTOOLS_WORKSPACE_PREFIX}{hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:IDENTIFIER_HASH_LENGTH]}"""
    stdout = run_backend_command(
        backend="semtools",
        stage="search",
        command=[
            "semtools",
            "search",
            "--json",
            "--top-k",
            str(top_k * SEMTOOLS_OVERFETCH_FACTOR),
            "--n-lines",
            str(SEMTOOLS_CONTEXT_LINES),
            "--workspace",
            workspace,
            "--",
            query,
            *[str(file) for file in files],
        ],
        cwd=root if root.is_dir() else root.parent,
        extra_env={},
        accepted_exit_codes=(0,),
        capture_stdout=True,
    )
    if isinstance(stdout, SemanticFailure):
        return stdout
    hits = parse_semtools_output(stdout=stdout)
    if isinstance(hits, SemanticFailure):
        return hits
    return SemanticSuccess(hits=hits)
