import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.mcp_install import (
    MCP_INSTALL_SCOPE,
    install_resolved_mcp_servers,
    resolve_install_path,
)
from stackops.scripts.python.helpers.helpers_agents.mcp_types import ResolvedMcpServer


@pytest.mark.parametrize("scope", ["workspace", "user"])
def test_install_scope_selects_target_without_changing_mcp_transport(scope: MCP_INSTALL_SCOPE, tmp_path: Path) -> None:
    project = tmp_path / "project"
    home = tmp_path / "home"
    server: ResolvedMcpServer = {
        "name": "example",
        "scope": "custom-file",
        "source_path": tmp_path / "catalog.json",
        "definition": {
            "transport": "stdio",
            "command": "example-mcp",
            "args": ["serve"],
            "env": {},
            "url": None,
            "headers": {},
            "cwd": None,
            "description": None,
            "enabled": True,
        },
    }

    target = install_resolved_mcp_servers(
        agent="opencode", scope=scope, resolved_servers=(server,), repo_root=project if scope == "workspace" else None, home_dir=home,
    )

    expected = project / ".opencode" / "opencode.jsonc" if scope == "workspace" else home / ".config" / "opencode" / "opencode.jsonc"
    assert target == expected
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "mcp": {"example": {"type": "local", "command": ["example-mcp", "serve"], "enabled": True}},
    }


def test_workspace_mcp_install_requires_repo_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Workspace MCP installation requires running inside a git repository"):
        resolve_install_path(agent="opencode", scope="workspace", repo_root=None, home_dir=tmp_path)
