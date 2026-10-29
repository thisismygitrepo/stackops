import json
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_seek.semantic.command_runner import run_backend_command
from stackops.scripts.python.helpers.helpers_seek.semantic.constants import GREPAI_CONFIG_RELATIVE_PATH
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import (
    SemanticFailure,
    SemanticHit,
    SemanticOutcome,
    SemanticSuccess,
)


class GrepaiRecord(TypedDict):
    file_path: str
    start_line: int
    end_line: int
    score: float
    content: str


class GrepaiError(TypedDict):
    error: str


def find_grepai_project_root(root: Path) -> Path | None:
    return next((candidate for candidate in (root, *root.parents) if candidate.joinpath(GREPAI_CONFIG_RELATIVE_PATH).is_file()), None)


def parse_grepai_output(stdout: str, project_root: Path) -> list[SemanticHit] | SemanticFailure:
    try:
        payload = cast(list[GrepaiRecord] | GrepaiError, json.loads(stdout))
        if isinstance(payload, dict):
            return SemanticFailure(backend="grepai", stage="search", message=payload["error"])
        return [
            SemanticHit(
                path=project_root / record["file_path"],
                start_line=record["start_line"],
                end_line=record["end_line"],
                focus_line=record["start_line"],
                metric="score",
                value=record["score"],
                content=record["content"].removeprefix(f"""File: {record["file_path"]}\n\n"""),
            )
            for record in payload
        ]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        return SemanticFailure(backend="grepai", stage="parse", message=f"""unexpected grepai output: {error!r}""")


def search_grepai(root: Path, query: str, extension: str | None, top_k: int) -> SemanticOutcome:
    if extension is not None:
        return SemanticFailure(backend="grepai", stage="options", message="grepai has no extension filter; run without --extension")
    project_root = find_grepai_project_root(root=root)
    if project_root is None:
        initialized = run_backend_command(
            backend="grepai",
            stage="index",
            command=["grepai", "init", "--yes"],
            cwd=root,
            extra_env={},
            accepted_exit_codes=(0,),
            capture_stdout=False,
        )
        if isinstance(initialized, SemanticFailure):
            return initialized
        project_root = root
    indexed = run_backend_command(
        backend="grepai",
        stage="index",
        command=["grepai", "index"],
        cwd=root,
        extra_env={},
        accepted_exit_codes=(0,),
        capture_stdout=False,
    )
    if isinstance(indexed, SemanticFailure):
        return indexed
    path_arguments = [] if root == project_root else ["--path", root.relative_to(project_root).as_posix()]
    stdout = run_backend_command(
        backend="grepai",
        stage="search",
        command=["grepai", "search", "--json", "-n", str(top_k), *path_arguments, "--", query],
        cwd=root,
        extra_env={},
        accepted_exit_codes=(0,),
        capture_stdout=True,
    )
    if isinstance(stdout, SemanticFailure):
        return stdout
    hits = parse_grepai_output(stdout=stdout, project_root=project_root)
    if isinstance(hits, SemanticFailure):
        return hits
    return SemanticSuccess(hits=hits)
