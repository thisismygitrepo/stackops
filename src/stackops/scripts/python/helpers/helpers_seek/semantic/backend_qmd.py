import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import TypedDict, cast

from stackops.scripts.python.helpers.helpers_seek.semantic.command_runner import run_backend_command
from stackops.scripts.python.helpers.helpers_seek.semantic.constants import (
    IDENTIFIER_HASH_LENGTH,
    QMD_COLLECTION_PREFIX,
    QMD_DEFAULT_EXTENSION,
    QMD_LOCAL_CONFIG_RELATIVE_PATHS,
)
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import (
    SemanticFailure,
    SemanticHit,
    SemanticOutcome,
    SemanticSuccess,
)


SNIPPET_HEADER = re.compile(r"@@ -(?P<start>\d+),(?P<count>\d+) @@[^\n]*\n")
UNRESOLVED_PATH_PREFIX = "qmd://"


class QmdRecord(TypedDict):
    score: float
    file: str
    line: int
    snippet: str


def has_qmd_local_index(root: Path) -> bool:
    return any(
        candidate.joinpath(config_relative_path).is_file()
        for candidate in (root, *root.parents)
        for config_relative_path in QMD_LOCAL_CONFIG_RELATIVE_PATHS
    )


def parse_qmd_output(stdout: str, root: Path) -> list[SemanticHit] | SemanticFailure:
    try:
        records = cast(list[QmdRecord], json.loads(stdout))
        hits: list[SemanticHit] = []
        for record in records:
            if record["file"].startswith(UNRESOLVED_PATH_PREFIX):
                return SemanticFailure(backend="qmd", stage="parse", message=f"""qmd could not resolve an on-disk path for {record["file"]}""")
            header = SNIPPET_HEADER.match(record["snippet"])
            if header is None:
                return SemanticFailure(backend="qmd", stage="parse", message=f"""unexpected qmd snippet format: {record["snippet"][:80]!r}""")
            start_line = int(header["start"])
            hits.append(
                SemanticHit(
                    path=root / record["file"],
                    start_line=start_line,
                    end_line=start_line + int(header["count"]) - 1,
                    focus_line=record["line"],
                    metric="score",
                    value=record["score"],
                    content=record["snippet"][header.end() :],
                )
            )
        return hits
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        return SemanticFailure(backend="qmd", stage="parse", message=f"""unexpected qmd output: {error!r}""")


def search_qmd(root: Path, query: str, extension: str | None, top_k: int) -> SemanticOutcome:
    glob = f"""**/*{QMD_DEFAULT_EXTENSION if extension is None else extension}"""
    collection = f"""{QMD_COLLECTION_PREFIX}{hashlib.sha256(f"{root}|{glob}".encode("utf-8")).hexdigest()[:IDENTIFIER_HASH_LENGTH]}"""
    working_directory_env = {"PWD": str(root)}
    needs_init = not has_qmd_local_index(root=root)
    collection_exists = (
        not needs_init
        and subprocess.run(
            ["qmd", "collection", "show", collection],
            cwd=root,
            env={**os.environ, **working_directory_env},
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    index_steps: list[list[str]] = []
    if needs_init:
        index_steps.append(["init"])
    index_steps.append(["update"] if collection_exists else ["collection", "add", ".", "--name", collection, "--mask", glob])
    index_steps.append(["embed", "-c", collection])
    for index_step in index_steps:
        indexed = run_backend_command(
            backend="qmd",
            stage="index",
            command=["qmd", *index_step],
            cwd=root,
            extra_env=working_directory_env,
            accepted_exit_codes=(0,),
            capture_stdout=False,
        )
        if isinstance(indexed, SemanticFailure):
            return indexed
    stdout = run_backend_command(
        backend="qmd",
        stage="search",
        command=["qmd", "vsearch", "--format", "json", "--full-path", "-n", str(top_k), "-c", collection, "--", query],
        cwd=root,
        extra_env=working_directory_env,
        accepted_exit_codes=(0,),
        capture_stdout=True,
    )
    if isinstance(stdout, SemanticFailure):
        return stdout
    hits = parse_qmd_output(stdout=stdout, root=root)
    if isinstance(hits, SemanticFailure):
        return hits
    return SemanticSuccess(hits=hits)
