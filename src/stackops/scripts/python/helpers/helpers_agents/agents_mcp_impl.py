from collections.abc import Callable
from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_agents.mcp_catalog import (
    collect_available_mcp_names,
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
)
from stackops.scripts.python.helpers.helpers_agents.mcp_types import MCP_CATALOG_WHERE
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import (
    build_agent_skill_install_commands,
    is_supported_agent_skill_name,
    run_agent_skill_install_commands,
)
from stackops.utils.accessories import get_repo_root

Reporter = Callable[[str], None]
_WORKSPACE_REPO_MARKER: Final[str] = ".git"
_WORKSPACE_REPO_MINIMUM: Final[int] = 2
_LOCAL_INSTALL_ROOT_REQUIREMENT: Final[str] = "running inside a git repository or from a workspace directory containing multiple git repositories"


def resolve_local_install_root(*, current_dir: Path) -> Path | None:
    repo_root = get_repo_root(current_dir)
    if repo_root is not None:
        return repo_root

    workspace_root = current_dir.expanduser().resolve()
    if not workspace_root.is_dir():
        return None

    try:
        child_paths = tuple(workspace_root.iterdir())
    except OSError as error:
        raise ValueError(f"Cannot inspect local install directory: {workspace_root}") from error

    nested_repo_count = 0
    for child_path in child_paths:
        if child_path.is_dir() and child_path.joinpath(_WORKSPACE_REPO_MARKER).exists():
            nested_repo_count += 1
            if nested_repo_count >= _WORKSPACE_REPO_MINIMUM:
                return workspace_root
    return None


def add_mcp(
    *, requested_mcp_servers: str | None, agents: str, scope: MCP_INSTALL_SCOPE, where: MCP_CATALOG_WHERE, edit: bool, report: Reporter
) -> None:
    search_locations = resolve_mcp_catalog_locations(where=where)
    if edit:
        created_catalog_paths: list[Path] = []
        for location in search_locations:
            if ensure_mcp_catalog_exists(location=location):
                created_catalog_paths.append(location["path"])
        for created_catalog_path in created_catalog_paths:
            report(f"Created MCP catalog template at: {created_catalog_path}")

        editable_catalog_paths = tuple(location["path"] for location in search_locations if location["path"].exists() and location["path"].is_file())
        if len(editable_catalog_paths) == 0:
            searched = ", ".join(str(location["path"]) for location in search_locations)
            raise ValueError(f"No MCP catalog files found for --where '{where}'. Searched: {searched}")
        for catalog_path in editable_catalog_paths:
            edit_mcp_catalog(path=catalog_path)

    if requested_mcp_servers is None:
        if edit:
            return
        if len(collect_available_mcp_names(locations=search_locations)) == 0:
            raise ValueError("No MCP servers are available to choose from in the selected catalog locations")
        requested_mcp_names = choose_requested_mcp_names(locations=search_locations)
    else:
        requested_mcp_names = parse_requested_mcp_names(raw_value=requested_mcp_servers)

    requested_skill_names = tuple(
        requested_mcp_name for requested_mcp_name in requested_mcp_names if is_supported_agent_skill_name(skill_name=requested_mcp_name)
    )
    if len(requested_skill_names) > 0:
        if len(requested_skill_names) != len(requested_mcp_names):
            raise ValueError("Do not mix MCP server names and agent skill names in one add-mcp invocation")

        selected_agents = parse_requested_agents(raw_value=agents)
        repo_root = resolve_local_install_root(current_dir=Path.cwd()) if scope == "local" else None
        if scope == "local" and repo_root is None:
            raise ValueError(f"Local skill installation requires {_LOCAL_INSTALL_ROOT_REQUIREMENT}")
        install_root = repo_root if repo_root is not None else Path.cwd()
        commands = build_agent_skill_install_commands(skill_names=requested_skill_names, agents=selected_agents, scope=scope)
        report(f"Installing agent skills through skills CLI: {', '.join(requested_skill_names)}")
        run_agent_skill_install_commands(install_root=install_root, commands=commands)
        return

    resolved_mcp_servers = resolve_requested_mcp_servers(requested_names=requested_mcp_names, locations=search_locations)
    selected_agents = parse_requested_agents(raw_value=agents)
    repo_root = resolve_local_install_root(current_dir=Path.cwd()) if scope == "local" else None
    if scope == "local" and repo_root is None:
        raise ValueError(f"Local MCP installation requires {_LOCAL_INSTALL_ROOT_REQUIREMENT}")

    report(f"Installing: {format_resolved_mcp_servers(resolved_mcp_servers)}")
    for selected_agent in selected_agents:
        install_path = install_resolved_mcp_servers(
            agent=selected_agent, scope=scope, resolved_servers=resolved_mcp_servers, repo_root=repo_root, home_dir=Path.home()
        )
        report(f"{selected_agent}: {install_path}")
