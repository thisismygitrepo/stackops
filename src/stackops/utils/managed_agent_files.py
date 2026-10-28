from pathlib import Path
from typing import Literal, TypeAlias, cast

from stackops.utils.managed_files import ManagedFileSpec
from stackops.utils.repos.constants import PROJECT_ROOT_REQUIREMENT

AgentManagedFileKind: TypeAlias = Literal["prompts", "parallel", "mcp"]
AgentManagedFileSource: TypeAlias = Literal["workspace", "w", "user", "u", "library", "l"]


def agent_managed_file_locations(*, kind: AgentManagedFileKind) -> tuple[tuple[AgentManagedFileSource, Path], ...]:
    import stackops.jobs.agents.mcps as mcp_assets
    import stackops.utils.schemas.agents as agent_schema_assets
    from stackops.utils.path_reference import get_path_reference_path
    from stackops.utils.repos.stackops_paths import current_repo_stackops_path
    from stackops.utils.source_of_truth import DOTFILES_STACKOPS_ROOT, LIBRARY_ROOT

    match kind:
        case "prompts":
            repo_path = current_repo_stackops_path(path_kind="prompts_yaml")
            relative_user_path = Path("agents/prompts/prompts.yaml")
            library_path = LIBRARY_ROOT / relative_user_path
        case "parallel":
            repo_path = current_repo_stackops_path(path_kind="parallel_yaml")
            relative_user_path = Path("agents/parallel/parallel.yaml")
            library_path = get_path_reference_path(module=agent_schema_assets, path_reference="parallel.yaml")
        case "mcp":
            repo_path = current_repo_stackops_path(path_kind="mcp_json")
            relative_user_path = Path("agents/mcps/mcp.json")
            library_path = get_path_reference_path(module=mcp_assets, path_reference=mcp_assets.MCP_PATH_REFERENCE)
    locations: list[tuple[AgentManagedFileSource, Path]] = [
        ("user", DOTFILES_STACKOPS_ROOT / relative_user_path),
        ("library", library_path),
    ]
    if repo_path is not None:
        locations.insert(0, ("workspace", repo_path))
    return tuple(locations)


def resolve_agent_managed_file_path(*, kind: AgentManagedFileKind, source: AgentManagedFileSource) -> Path:
    match source:
        case "workspace" | "w":
            source = "workspace"
        case "user" | "u":
            source = "user"
        case "library" | "l":
            source = "library"
    for location_source, path in agent_managed_file_locations(kind=kind):
        if location_source == source:
            return path
    if source == "workspace":
        raise ValueError(f"""--source workspace requires {PROJECT_ROOT_REQUIREMENT}; use --custom-path for an explicit configuration file""")
    raise ValueError(f"""Unsupported agent configuration source: {source}""")


def get_agent_managed_file_spec(kind: AgentManagedFileKind) -> ManagedFileSpec:
    import stackops.utils.schemas.agents as agent_schema_assets
    from stackops.utils.path_reference import get_path_reference_path

    user_path = dict(agent_managed_file_locations(kind=kind)).get("workspace")
    if user_path is None:
        relative_path = ".stackops/mcp.json" if kind == "mcp" else f""".stackops/agents/{kind}.yaml"""
        user_path = Path.cwd() / relative_path
    match kind:
        case "prompts":
            from stackops.scripts.python.helpers.helpers_agents.agents_run_context import prompts_yaml_template

            schema_path = get_path_reference_path(module=agent_schema_assets, path_reference="prompts.schema.json")
            example_path = resolve_agent_managed_file_path(kind=kind, source="library")
            initial_content = prompts_yaml_template()
        case "parallel":
            schema_path = get_path_reference_path(module=agent_schema_assets, path_reference="parallel.schema.json")
            example_path = get_path_reference_path(module=agent_schema_assets, path_reference="parallel.yaml")
            initial_content = example_path.read_text(encoding="utf-8")
        case "mcp":
            import stackops.jobs.agents.mcps as mcp_assets

            schema_path = get_path_reference_path(module=mcp_assets, path_reference=mcp_assets.MCP_SCHEMA_PATH_REFERENCE)
            example_path = get_path_reference_path(module=mcp_assets, path_reference=mcp_assets.MCP_PATH_REFERENCE)
            initial_content = '{"$schema": "./mcp.schema.json", "mcpServers": {}}\n'
    return ManagedFileSpec(
        user_path=user_path,
        example_source_path=example_path,
        schema_source_path=schema_path,
        initial_content=initial_content,
        file_mode=0o644,
    )


def validate_agent_managed_file(*, kind: AgentManagedFileKind, data_path: Path) -> None:
    from stackops.utils.files.read import read_json, read_yaml

    raw_data: object = read_json(data_path) if kind == "mcp" else read_yaml(data_path)
    if not isinstance(raw_data, dict):
        raise ValueError(f"""Agent {kind} configuration must be an object: {data_path}""")
    if not all(isinstance(key, str) for key in raw_data):
        raise ValueError(f"""Agent {kind} configuration must use string keys: {data_path}""")
    entries = cast(dict[str, object], raw_data)
    match kind:
        case "prompts":
            from stackops.scripts.python.helpers.helpers_agents.agents_run_context import collect_named_yaml_candidates

            collect_named_yaml_candidates(raw_data=entries, prefix="", group=None)
        case "parallel":
            from stackops.scripts.python.helpers.helpers_agents.agents_parallel_run_yaml import (
                parse_parallel_create_values,
                validate_parallel_run_name,
            )

            for name, entry in entries.items():
                validate_parallel_run_name(entry_name=name)
                parse_parallel_create_values(raw_entry=entry, entry_name=name)
        case "mcp":
            from stackops.scripts.python.helpers.helpers_agents.mcp_catalog import resolve_requested_mcp_servers

            servers = entries.get("mcpServers")
            if not isinstance(servers, dict) or not all(isinstance(name, str) for name in servers):
                raise ValueError(f"""MCP catalog must define mcpServers as an object with string keys: {data_path}""")
            resolve_requested_mcp_servers(requested_names=tuple(cast(dict[str, object], servers)), locations=({"scope": "workspace", "path": data_path},))
