from __future__ import annotations

import stackops.utils.schemas.repos as repos_schema


def test_repos_schema_reference_matches_expected_filename() -> None:
    assert repos_schema.REPOS_SCHEMA_PATH_REFERENCE == "repos_schema.json"
