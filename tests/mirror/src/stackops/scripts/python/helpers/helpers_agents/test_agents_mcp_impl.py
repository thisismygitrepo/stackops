import json
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents import agents_mcp_impl
from stackops.scripts.python.helpers.helpers_agents.mcp_types import McpCatalogLocation, ResolvedMcpServer


def test_add_mcp_runs_mixed_skill_and_mcp_selection(monkeypatch, tmp_path: Path) -> None:
    catalog_path = tmp_path / "mcp.json"
    catalog_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "alpha": {
                        "command": "uvx",
                        "args": ["alpha-mcp"],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    locations: tuple[McpCatalogLocation, ...] = ({"scope": "repo", "path": catalog_path},)
    reports: list[str] = []
    observed: dict[str, object] = {}

    def fake_resolve_mcp_catalog_locations(*, source: object) -> tuple[McpCatalogLocation, ...]:
        observed["source"] = source
        return locations

    def fake_resolve_local_install_root(*, current_dir: Path) -> Path:
        observed["current_dir"] = current_dir
        return tmp_path

    def fake_run_agent_skill_install_commands(*, install_root: Path, commands: tuple[tuple[str, ...], ...]) -> int:
        observed["skill_install_root"] = install_root
        observed["skill_commands"] = commands
        return 0

    def fake_install_resolved_mcp_servers(
        *, agent: str, scope: str, resolved_servers: tuple[ResolvedMcpServer, ...], repo_root: Path | None, home_dir: Path
    ) -> Path:
        observed["mcp_agent"] = agent
        observed["mcp_scope"] = scope
        observed["mcp_names"] = tuple(resolved_server["name"] for resolved_server in resolved_servers)
        observed["mcp_repo_root"] = repo_root
        observed["home_dir"] = home_dir
        return tmp_path / ".codex" / "config.toml"

    monkeypatch.setattr(agents_mcp_impl, "resolve_mcp_catalog_locations", fake_resolve_mcp_catalog_locations)
    monkeypatch.setattr(agents_mcp_impl, "resolve_local_install_root", fake_resolve_local_install_root)
    monkeypatch.setattr(agents_mcp_impl, "run_agent_skill_install_commands", fake_run_agent_skill_install_commands)
    monkeypatch.setattr(agents_mcp_impl, "install_resolved_mcp_servers", fake_install_resolved_mcp_servers)

    agents_mcp_impl.add_mcp(
        requested_mcp_servers="agent-skills,alpha",
        agents="codex",
        scope="local",
        source="all",
        edit=False,
        report=reports.append,
    )

    assert observed["skill_install_root"] == tmp_path
    assert observed["skill_commands"] == (
        (
            "bunx",
            "skills@latest",
            "add",
            "addyosmani/agent-skills",
            "--agent",
            "codex",
        ),
    )
    assert observed["mcp_agent"] == "codex"
    assert observed["mcp_scope"] == "local"
    assert observed["mcp_names"] == ("alpha",)
    assert observed["mcp_repo_root"] == tmp_path
    assert reports[0] == "Installing agent skills through skills CLI: agent-skills"
    assert reports[1] == "Installing: alpha (repo)"
