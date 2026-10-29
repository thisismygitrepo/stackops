import json
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_seek.semantic.command_runner import run_backend_command
from stackops.scripts.python.helpers.helpers_seek.semantic.constants import CK_NO_MATCH_EXIT_CODE
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import (
    SemanticFailure,
    SemanticHit,
    SemanticOutcome,
    SemanticSuccess,
)


class CkSpan(TypedDict):
    line_start: int
    line_end: int


class CkRecord(TypedDict):
    path: str
    span: CkSpan
    snippet: str
    score: float


def parse_ck_output(stdout: str, root: Path) -> list[SemanticHit] | SemanticFailure:
    try:
        records = cast(list[CkRecord], [json.loads(line) for line in stdout.splitlines() if line != ""])
        return [
            SemanticHit(
                path=root / record["path"],
                start_line=record["span"]["line_start"],
                end_line=record["span"]["line_end"],
                focus_line=record["span"]["line_start"],
                metric="score",
                value=record["score"],
                content=record["snippet"],
            )
            for record in records
        ]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        return SemanticFailure(backend="ck", stage="parse", message=f"""unexpected ck output: {error!r}""")


def search_ck(root: Path, query: str, extension: str | None, top_k: int) -> SemanticOutcome:
    target = "." if extension is None else f"**/*{extension}"
    stdout = run_backend_command(
        backend="ck",
        stage="search",
        command=["ck", "--jsonl", "--sem", "--full-section", "--topk", str(top_k), "--", query, target],
        cwd=root,
        extra_env={},
        accepted_exit_codes=(0, CK_NO_MATCH_EXIT_CODE),
        capture_stdout=True,
    )
    if isinstance(stdout, SemanticFailure):
        return stdout
    hits = parse_ck_output(stdout=stdout, root=root)
    if isinstance(hits, SemanticFailure):
        return hits
    return SemanticSuccess(hits=hits)
