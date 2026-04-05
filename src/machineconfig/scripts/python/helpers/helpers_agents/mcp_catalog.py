from collections.abc import Sequence
import json
from pathlib import Path
import shutil
import subprocess

from machineconfig.scripts.python.helpers.helpers_agents.mcp_types import (
    McpCatalogFile,
    McpCatalogLocation,
    MCP_CATALOG_WHERE,
    McpServerDefinitionRaw,
    ResolvedMcpServer,
    ResolvedMcpServerDefinition,
)
from machineconfig.utils.files.read import read_json


def parse_requested_mcp_names(raw_value: str) -> tuple[str, ...]:
    if raw_value.strip() == "":
        raise ValueError("Provide at least one MCP server name")

    parts = [part.strip() for part in raw_value.split(",")]
    if any(part == "" for part in parts):
        raise ValueError("MCP server names must be a comma-separated list without empty entries")

    seen: set[str] = set()
    duplicates: list[str] = []
    for part in parts:
        if part in seen:
            duplicates.append(part)
            continue
        seen.add(part)
    if len(duplicates) > 0:
        raise ValueError(f"Duplicate MCP server names are not allowed: {', '.join(dict.fromkeys(duplicates))}")

    return tuple(parts)


def default_mcp_catalog_locations() -> tuple[McpCatalogLocation, ...]:
    from machineconfig.utils.source_of_truth import CONFIG_ROOT, DOTFILES_MCFG_ROOT, LIBRARY_ROOT

    return (
        {"scope": "private", "path": DOTFILES_MCFG_ROOT / "agents" / "mcps" / "mcp.json"},
        {"scope": "public", "path": CONFIG_ROOT / "agents" / "mcps" / "mcp.json"},
        {"scope": "library", "path": LIBRARY_ROOT / "jobs" / "agents" / "mcps" / "mcp.json"},
    )


def resolve_mcp_catalog_locations(where: MCP_CATALOG_WHERE) -> tuple[McpCatalogLocation, ...]:
    locations = default_mcp_catalog_locations()
    match where:
        case "all" | "a":
            return locations
        case "private" | "p":
            return (locations[0],)
        case "public" | "b":
            return (locations[1],)
        case "library" | "l":
            return (locations[2],)


def _mcp_catalog_template() -> str:
    return json.dumps({"mcpServers": {}}, indent=2) + "\n"


def ensure_mcp_catalog_exists(location: McpCatalogLocation) -> bool:
    catalog_path = location["path"]
    if catalog_path.exists():
        if not catalog_path.is_file():
            raise ValueError(f"MCP catalog path exists but is not a file: {catalog_path}")
        return False

    if location["scope"] == "library":
        return False

    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(_mcp_catalog_template(), encoding="utf-8")
    return True


def edit_mcp_catalog(path: Path) -> None:
    editor = shutil.which("hx")
    if editor is None:
        editor = shutil.which("nano")
    if editor is None:
        raise ValueError("No supported editor found. Install 'hx' or 'nano', or run without --edit")

    result = subprocess.run([editor, str(path)], check=False)
    if result.returncode != 0:
        raise ValueError(f"Editor exited with status code {result.returncode}")


def _validate_non_empty_string(raw_value: object, *, field_name: str, server_name: str, path: Path) -> str:
    if not isinstance(raw_value, str) or raw_value.strip() == "":
        raise ValueError(f"MCP catalog entry '{server_name}' in {path} must define a non-empty string for '{field_name}'")
    return raw_value


def _validate_string_list(raw_value: object, *, field_name: str, server_name: str, path: Path) -> list[str]:
    if not isinstance(raw_value, list):
        raise ValueError(f"MCP catalog entry '{server_name}' in {path} must define '{field_name}' as a list[str]")

    values: list[str] = []
    for item in raw_value:
        if not isinstance(item, str):
            raise ValueError(f"MCP catalog entry '{server_name}' in {path} must define '{field_name}' as a list[str]")
        values.append(item)
    return values


def _validate_string_map(raw_value: object, *, field_name: str, server_name: str, path: Path) -> dict[str, str]:
    if not isinstance(raw_value, dict):
        raise ValueError(f"MCP catalog entry '{server_name}' in {path} must define '{field_name}' as a dict[str, str]")

    values: dict[str, str] = {}
    for raw_key, raw_item in raw_value.items():
        if not isinstance(raw_key, str) or not isinstance(raw_item, str):
            raise ValueError(f"MCP catalog entry '{server_name}' in {path} must define '{field_name}' as a dict[str, str]")
        values[raw_key] = raw_item
    return values


def _load_mcp_catalog(path: Path) -> McpCatalogFile:
    raw_catalog_object: object = read_json(path)
    if not isinstance(raw_catalog_object, dict):
        raise ValueError(f"MCP catalog at {path} must be a JSON object")

    raw_servers_object = raw_catalog_object.get("mcpServers")
    if not isinstance(raw_servers_object, dict):
        raise ValueError(f"MCP catalog at {path} must define 'mcpServers' as an object")

    validated_servers: dict[str, McpServerDefinitionRaw] = {}
    for raw_server_name, raw_definition_object in raw_servers_object.items():
        if not isinstance(raw_server_name, str) or raw_server_name.strip() == "":
            raise ValueError(f"MCP catalog at {path} contains an invalid server name")
        if not isinstance(raw_definition_object, dict):
            raise ValueError(f"MCP catalog entry '{raw_server_name}' in {path} must be a JSON object")

        validated_definition: McpServerDefinitionRaw = {}
        for raw_field_name, raw_field_value in raw_definition_object.items():
            if not isinstance(raw_field_name, str):
                raise ValueError(f"MCP catalog entry '{raw_server_name}' in {path} contains a non-string field name")

            match raw_field_name:
                case "command" | "url" | "cwd" | "description":
                    validated_definition[raw_field_name] = _validate_non_empty_string(
                        raw_field_value,
                        field_name=raw_field_name,
                        server_name=raw_server_name,
                        path=path,
                    )
                case "args":
                    validated_definition["args"] = _validate_string_list(
                        raw_field_value,
                        field_name=raw_field_name,
                        server_name=raw_server_name,
                        path=path,
                    )
                case "env" | "headers":
                    validated_definition[raw_field_name] = _validate_string_map(
                        raw_field_value,
                        field_name=raw_field_name,
                        server_name=raw_server_name,
                        path=path,
                    )
                case "enabled":
                    if not isinstance(raw_field_value, bool):
                        raise ValueError(f"MCP catalog entry '{raw_server_name}' in {path} must define 'enabled' as a bool")
                    validated_definition["enabled"] = raw_field_value
                case _:
                    raise ValueError(f"MCP catalog entry '{raw_server_name}' in {path} contains an unsupported field '{raw_field_name}'")

        validated_servers[raw_server_name] = validated_definition

    return {"mcpServers": validated_servers}


def _normalize_server_definition(raw_definition: McpServerDefinitionRaw, *, server_name: str, path: Path) -> ResolvedMcpServerDefinition:
    has_command = "command" in raw_definition
    has_url = "url" in raw_definition
    if has_command == has_url:
        raise ValueError(f"MCP catalog entry '{server_name}' in {path} must define exactly one of 'command' or 'url'")

    description = raw_definition["description"] if "description" in raw_definition else None
    enabled = raw_definition["enabled"] if "enabled" in raw_definition else True

    if has_command:
        if "headers" in raw_definition:
            raise ValueError(f"MCP catalog entry '{server_name}' in {path} cannot define 'headers' for stdio transport")
        return {
            "transport": "stdio",
            "command": raw_definition["command"],
            "args": raw_definition["args"] if "args" in raw_definition else [],
            "env": raw_definition["env"] if "env" in raw_definition else {},
            "url": None,
            "headers": {},
            "cwd": raw_definition["cwd"] if "cwd" in raw_definition else None,
            "description": description,
            "enabled": enabled,
        }

    if "args" in raw_definition or "env" in raw_definition or "cwd" in raw_definition:
        raise ValueError(f"MCP catalog entry '{server_name}' in {path} cannot define 'args', 'env', or 'cwd' for HTTP transport")

    url = raw_definition["url"] if "url" in raw_definition else None
    if url is None:
        raise ValueError(f"MCP catalog entry '{server_name}' in {path} must define 'url' for HTTP transport")

    return {
        "transport": "http",
        "command": None,
        "args": [],
        "env": {},
        "url": url,
        "headers": raw_definition["headers"] if "headers" in raw_definition else {},
        "cwd": None,
        "description": description,
        "enabled": enabled,
    }


def resolve_requested_mcp_servers(
    requested_names: Sequence[str],
    *,
    locations: Sequence[McpCatalogLocation] | None = None,
) -> tuple[ResolvedMcpServer, ...]:
    if len(requested_names) == 0:
        return ()

    search_locations = tuple(locations) if locations is not None else default_mcp_catalog_locations()
    if len(search_locations) == 0:
        raise ValueError("No MCP catalog locations are configured")

    loaded_catalogs: dict[Path, McpCatalogFile] = {}
    existing_locations: list[McpCatalogLocation] = []
    for location in search_locations:
        catalog_path = location["path"]
        if not catalog_path.exists():
            continue
        if not catalog_path.is_file():
            raise ValueError(f"MCP catalog path exists but is not a file: {catalog_path}")
        loaded_catalogs[catalog_path] = _load_mcp_catalog(catalog_path)
        existing_locations.append(location)

    searched_paths = ", ".join(str(location["path"]) for location in search_locations)
    if len(existing_locations) == 0:
        raise ValueError(f"No MCP catalog files were found. Searched: {searched_paths}")

    resolved_servers: list[ResolvedMcpServer] = []
    missing_servers: list[str] = []
    for requested_name in requested_names:
        resolved_server: ResolvedMcpServer | None = None
        for location in existing_locations:
            catalog_path = location["path"]
            catalog = loaded_catalogs[catalog_path]
            if requested_name not in catalog["mcpServers"]:
                continue

            raw_definition = catalog["mcpServers"][requested_name]
            resolved_server = {
                "name": requested_name,
                "scope": location["scope"],
                "source_path": catalog_path,
                "definition": _normalize_server_definition(raw_definition, server_name=requested_name, path=catalog_path),
            }
            break

        if resolved_server is None:
            missing_servers.append(requested_name)
            continue

        resolved_servers.append(resolved_server)

    if len(missing_servers) > 0:
        raise ValueError(f"MCP servers not found: {', '.join(missing_servers)}. Searched: {searched_paths}")

    return tuple(resolved_servers)


def format_resolved_mcp_servers(resolved_servers: Sequence[ResolvedMcpServer]) -> str:
    return ", ".join(f"""{resolved_server["name"]} ({resolved_server["scope"]})""" for resolved_server in resolved_servers)
