import json
from pathlib import Path

from stackops.scripts.python.helpers.helpers_seek.semantic.backend_ck import parse_ck_output
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_grepai import parse_grepai_output
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_qmd import parse_qmd_output
from stackops.scripts.python.helpers.helpers_seek.semantic.backend_semtools import parse_semtools_output
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticFailure, SemanticHit


def test_semtools_converts_zero_based_exclusive_lines_to_one_based_inclusive_lines() -> None:
    stdout = json.dumps(
        {
            "results": [
                {
                    "filename": "/repo/a.py",
                    "start_line_number": 0,
                    "end_line_number": 5,
                    "match_line_number": 1,
                    "distance": 0.7693150800058302,
                    "content": "def retry_with_backoff(fn):\n    for attempt in range(5):",
                }
            ]
        }
    )

    assert parse_semtools_output(stdout=stdout) == [
        SemanticHit(
            path=Path("/repo/a.py"),
            start_line=1,
            end_line=5,
            focus_line=2,
            metric="distance",
            value=0.7693150800058302,
            content="def retry_with_backoff(fn):\n    for attempt in range(5):",
        )
    ]


def test_semtools_reports_unexpected_output_as_parse_failure() -> None:
    failure = parse_semtools_output(stdout=json.dumps({"hits": []}))

    assert isinstance(failure, SemanticFailure)
    assert (failure.backend, failure.stage) == ("semtools", "parse")


def test_ck_reads_jsonl_records_and_keeps_absolute_paths() -> None:
    record = {
        "path": "/repo/installer_utils/installer_class.py",
        "span": {"byte_start": 16561, "byte_end": 18332, "line_start": 292, "line_end": 321},
        "language": "python",
        "snippet": "    def binary_download(self) -> None:\n        pass",
        "score": 0.8718,
    }

    assert parse_ck_output(stdout=json.dumps(record) + "\n", root=Path("/elsewhere")) == [
        SemanticHit(
            path=Path("/repo/installer_utils/installer_class.py"),
            start_line=292,
            end_line=321,
            focus_line=292,
            metric="score",
            value=0.8718,
            content="    def binary_download(self) -> None:\n        pass",
        )
    ]


def test_ck_treats_empty_output_as_no_hits_and_malformed_output_as_failure() -> None:
    assert parse_ck_output(stdout="", root=Path("/repo")) == []
    failure = parse_ck_output(stdout="not json\n", root=Path("/repo"))
    assert isinstance(failure, SemanticFailure)
    assert (failure.backend, failure.stage) == ("ck", "parse")


def test_grepai_resolves_paths_against_project_root_and_strips_file_header() -> None:
    record = {
        "file_path": "installer_utils/github_release_bulk.py",
        "start_line": 1,
        "end_line": 64,
        "score": 0.39562827,
        "content": "File: installer_utils/github_release_bulk.py\n\n#!/usr/bin/env python3\n",
    }

    assert parse_grepai_output(stdout=json.dumps([record]), project_root=Path("/project")) == [
        SemanticHit(
            path=Path("/project/installer_utils/github_release_bulk.py"),
            start_line=1,
            end_line=64,
            focus_line=1,
            metric="score",
            value=0.39562827,
            content="#!/usr/bin/env python3\n",
        )
    ]
    assert parse_grepai_output(stdout="[]", project_root=Path("/project")) == []


def test_grepai_error_payload_with_zero_exit_code_becomes_search_failure() -> None:
    message = 'Ollama returned status 404: {"error":"model \\"nomic-embed-text\\" not found, try pulling it first"}'

    failure = parse_grepai_output(stdout=json.dumps({"error": message}), project_root=Path("/project"))

    assert failure == SemanticFailure(backend="grepai", stage="search", message=message)


def test_qmd_strips_snippet_header_and_derives_line_range_from_it() -> None:
    record = {
        "score": 0.55,
        "file": "./installer_utils/github_release_bulk.py",
        "line": 4,
        "title": "github_release_bulk",
        "snippet": '@@ -3,4 @@ (2 before, 138 after)\nScript to fetch GitHub release information.\n"""',
    }

    assert parse_qmd_output(stdout=json.dumps([record]), root=Path("/project")) == [
        SemanticHit(
            path=Path("/project/installer_utils/github_release_bulk.py"),
            start_line=3,
            end_line=6,
            focus_line=4,
            metric="score",
            value=0.55,
            content='Script to fetch GitHub release information.\n"""',
        )
    ]
    assert parse_qmd_output(stdout="[]", root=Path("/project")) == []


def test_qmd_rejects_unresolved_paths_and_unknown_snippet_formats() -> None:
    unresolved = {"score": 0.5, "file": "qmd://seek-1/a.py", "line": 1, "title": "a", "snippet": "@@ -1,1 @@ (0 before, 0 after)\nx"}
    headerless = {"score": 0.5, "file": "./a.py", "line": 1, "title": "a", "snippet": "x"}

    for record in (unresolved, headerless):
        failure = parse_qmd_output(stdout=json.dumps([record]), root=Path("/project"))
        assert isinstance(failure, SemanticFailure)
        assert (failure.backend, failure.stage) == ("qmd", "parse")
