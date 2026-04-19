

from pathlib import Path
from typing import get_args

from stackops.scripts.python.helpers.helpers_agents import mcp_types as module


def test_literal_domains_and_typed_dict_shapes_are_runtime_usable() -> None:
    assert get_args(module.MCP_CATALOG_SCOPE) == ("private", "public", "library")
    assert get_args(module.MCP_CATALOG_WHERE) == ("all", "a", "private", "p", "public", "b", "library", "l")
    assert get_args(module.MCP_TRANSPORT) == ("stdio", "http")

    location: module.McpCatalogLocation = {"scope": "public", "path": Path("/tmp/mcp.json")}
    resolved_server: module.ResolvedMcpServer = {
        "name": "demo",
        "scope": location["scope"],
        "source_path": location["path"],
        "definition": {
            "transport": "stdio",
            "command": "uvx",
            "args": ["demo-server"],
            "env": {"TOKEN": "value"},
            "url": None,
            "headers": {},
            "cwd": None,
            "description": "demo",
            "enabled": True,
        },
    }

    assert resolved_server["source_path"] == Path("/tmp/mcp.json")
    assert resolved_server["definition"]["transport"] == "stdio"
