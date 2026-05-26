import json
from pathlib import Path
from typing import get_args

from stackops.scripts.python.helpers.helpers_agents import agents_run_impl
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS
from stackops.scripts.python.helpers.helpers_agents.mcp_install import install_resolved_mcp_servers, parse_requested_agents
from stackops.scripts.python.helpers.helpers_agents.mcp_types import ResolvedMcpServer


def _resolved_http_server(name: str) -> ResolvedMcpServer:
    return {
        "name": name,
        "scope": "library",
        "source_path": Path("mcp.json"),
        "definition": {
            "transport": "http",
            "command": None,
            "args": [],
            "env": {},
            "url": "https://mcp.example.com/github",
            "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"},
            "cwd": None,
            "description": "GitHub MCP",
            "enabled": True,
        },
    }


def test_agent_choices_use_oz_not_warp_cli() -> None:
    agent_values = get_args(AGENTS)

    assert "oz" in agent_values
    assert "warp-cli" not in agent_values
    assert "oz" in parse_requested_agents("oz")


def test_build_oz_agent_command_uses_current_cli_shape(tmp_path: Path, monkeypatch) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("hello", encoding="utf-8")
    mcp_file = tmp_path / "mcp.json"

    monkeypatch.setattr(agents_run_impl, "get_repo_root", lambda _: tmp_path)
    monkeypatch.setattr(agents_run_impl, "resolve_oz_mcp_config_paths", lambda **_: [mcp_file])

    command = agents_run_impl.build_agent_command(
        agent="oz",
        prompt_file=prompt_file,
        reasoning_effort=None,
        model="claude-sonnet-4",
        is_windows=False,
    )

    assert command == f'oz agent run --model claude-sonnet-4 --mcp {mcp_file} --prompt "$(cat {prompt_file})"'


def test_oz_mcp_install_writes_direct_mcp_file_shape(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    install_path = install_resolved_mcp_servers(
        agent="oz",
        scope="local",
        resolved_servers=(_resolved_http_server("github"),),
        repo_root=repo_root,
        home_dir=tmp_path,
    )

    assert install_path == repo_root / ".warp" / "mcp.json"
    assert json.loads(install_path.read_text(encoding="utf-8")) == {
        "github": {
            "url": "https://mcp.example.com/github",
            "headers": {"Authorization": "Bearer ${GITHUB_TOKEN}"},
        }
    }
