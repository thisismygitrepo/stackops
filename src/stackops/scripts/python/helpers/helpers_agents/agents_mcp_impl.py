from collections.abc import Callable
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_edit_source import choose_edit_source
from stackops.scripts.python.helpers.helpers_agents.mcp_catalog import (
    edit_mcp_catalog,
    ensure_mcp_catalog_exists,
    format_resolved_mcp_servers,
    parse_requested_mcp_names,
    resolve_mcp_catalog_locations,
    resolve_requested_mcp_servers,
)
from stackops.scripts.python.helpers.helpers_agents.mcp_install import (
    MCP_INSTALL_SCOPE,
    choose_requested_mcp_names,
    install_resolved_mcp_servers,
    parse_requested_agents,
    resolve_install_path,
)
from stackops.scripts.python.helpers.helpers_agents.mcp_types import MCP_CATALOG_SOURCE, McpCatalogLocation
from stackops.utils.repos.constants import PROJECT_ROOT_REQUIREMENT
from stackops.utils.repos.project import resolve_project_root

Reporter = Callable[[str], None]


def add_mcp(
    *,
    requested_mcp_servers: str | None,
    agents: str,
    scope: MCP_INSTALL_SCOPE,
    source: MCP_CATALOG_SOURCE,
    custom_path: Path | None,
    edit: bool,
    report: Reporter,
) -> None:
    search_locations: tuple[McpCatalogLocation, ...] = resolve_mcp_catalog_locations(source=source, custom_path=custom_path)
    if edit and custom_path is None and source in ("all", "a"):
        source, selected_catalog_path = choose_edit_source(locations=[(location["scope"], location["path"]) for location in search_locations])
        search_locations = ({"scope": source, "path": selected_catalog_path},)
    if edit:
        created_catalog_paths: list[Path] = []
        for location in search_locations:
            should_create_or_validate = location["scope"] != "workspace" or location["path"].exists() or source in ("workspace", "w")
            if should_create_or_validate and ensure_mcp_catalog_exists(location=location):
                created_catalog_paths.append(location["path"])
        for created_catalog_path in created_catalog_paths:
            report(f"Created MCP catalog template at: {created_catalog_path}")

        editable_catalog_paths = tuple(location["path"] for location in search_locations if location["path"].exists() and location["path"].is_file())
        if len(editable_catalog_paths) == 0:
            searched = ", ".join(str(location["path"]) for location in search_locations)
            raise ValueError(f"No MCP catalog files found for --source '{source}'. Searched: {searched}")
        for catalog_path in editable_catalog_paths:
            edit_mcp_catalog(path=catalog_path)

    if requested_mcp_servers is None:
        if edit:
            return
        requested_mcp_names = choose_requested_mcp_names(locations=search_locations)
    else:
        requested_mcp_names = parse_requested_mcp_names(raw_value=requested_mcp_servers)

    repo_root = resolve_project_root(current_dir=Path.cwd()) if scope == "workspace" else None
    if scope == "workspace" and repo_root is None:
        raise ValueError(f"""Workspace installation requires {PROJECT_ROOT_REQUIREMENT}""")

    resolved_mcp_servers = resolve_requested_mcp_servers(requested_names=requested_mcp_names, locations=search_locations)
    selected_agents = parse_requested_agents(raw_value=agents, scope=scope)
    home_dir = Path.home()
    for selected_agent in selected_agents:
        resolve_install_path(agent=selected_agent, scope=scope, repo_root=repo_root, home_dir=home_dir)

    report(f"Installing: {format_resolved_mcp_servers(resolved_mcp_servers)}")
    for selected_agent in selected_agents:
        install_path = install_resolved_mcp_servers(
            agent=selected_agent, scope=scope, resolved_servers=resolved_mcp_servers, repo_root=repo_root, home_dir=home_dir
        )
        report(f"{selected_agent}: {install_path}")
