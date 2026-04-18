from __future__ import annotations

from stackops.jobs.agents import mcps


def test_mcp_path_references_match_repo_files() -> None:
    assert mcps.MCP_PATH_REFERENCE == "mcp.json"
    assert mcps.MCP_SCHEMA_PATH_REFERENCE == "mcp.schema.json"
