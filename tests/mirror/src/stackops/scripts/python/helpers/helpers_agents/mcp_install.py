import json
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents import mcp_install
from stackops.scripts.python.helpers.helpers_agents.mcp_types import ResolvedMcpServer


def test_agy_mcp_install_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"

    local_path = mcp_install.resolve_install_path(agent="agy", scope="local", repo_root=repo_root, home_dir=tmp_path)
    global_path = mcp_install.resolve_install_path(agent="agy", scope="global", repo_root=None, home_dir=tmp_path)

    assert local_path == repo_root / ".agents" / "mcp_config.json"
    assert global_path == tmp_path / ".gemini" / "antigravity-cli" / "mcp_config.json"


def test_agy_mcp_install_uses_antigravity_server_url(tmp_path: Path) -> None:
    resolved_servers: tuple[ResolvedMcpServer, ...] = (
        {
            "name": "local-tool",
            "scope": "repo",
            "source_path": tmp_path / "catalog.json",
            "definition": {
                "transport": "stdio",
                "command": "bunx",
                "args": ["tool@latest"],
                "env": {"TOKEN": "value"},
                "url": None,
                "headers": {},
                "cwd": "/tmp/work",
                "description": None,
                "enabled": True,
            },
        },
        {
            "name": "remote-tool",
            "scope": "repo",
            "source_path": tmp_path / "catalog.json",
            "definition": {
                "transport": "http",
                "command": None,
                "args": [],
                "env": {},
                "url": "https://example.test/mcp",
                "headers": {"Authorization": "Bearer $TOKEN"},
                "cwd": None,
                "description": None,
                "enabled": True,
            },
        },
    )

    install_path = mcp_install.install_resolved_mcp_servers(
        agent="agy",
        scope="global",
        resolved_servers=resolved_servers,
        repo_root=None,
        home_dir=tmp_path,
    )

    assert install_path == tmp_path / ".gemini" / "antigravity-cli" / "mcp_config.json"
    assert json.loads(install_path.read_text(encoding="utf-8")) == {
        "mcpServers": {
            "local-tool": {
                "command": "bunx",
                "args": ["tool@latest"],
                "env": {"TOKEN": "value"},
                "cwd": "/tmp/work",
            },
            "remote-tool": {
                "serverUrl": "https://example.test/mcp",
                "headers": {"Authorization": "Bearer $TOKEN"},
            },
        }
    }
