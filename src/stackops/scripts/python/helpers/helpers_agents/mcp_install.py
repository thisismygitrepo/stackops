import json
import os
from pathlib import Path
from platform import system
import re
from typing import Final, Literal, cast, get_args

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS
from stackops.scripts.python.helpers.helpers_agents.mcp_catalog import collect_available_mcp_names
from stackops.scripts.python.helpers.helpers_agents.mcp_types import McpCatalogLocation, ResolvedMcpServer
from stackops.utils.io import remove_c_style_comments
from stackops.utils.options import choose_from_options


MCP_INSTALL_SCOPE = Literal["local", "global"]

_AGENT_VALUES: Final[tuple[AGENTS, ...]] = cast(tuple[AGENTS, ...], get_args(AGENTS))
_AUTHORIZATION_BEARER_ENV_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""^Bearer\s+\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|(?P<plain>[A-Za-z_][A-Za-z0-9_]*))$"""
)


def parse_requested_agents(raw_value: str) -> tuple[AGENTS, ...]:
    if raw_value.strip() == "":
        return _AGENT_VALUES

    parts = [part.strip() for part in raw_value.split(",")]
    if any(part == "" for part in parts):
        raise ValueError("Agent names must be a comma-separated list without empty entries")

    resolved_agents: list[AGENTS] = []
    seen_agents: set[str] = set()
    for part in parts:
        if part not in _AGENT_VALUES:
            raise ValueError(f"Unsupported agent: {part}. Supported agents: {', '.join(_AGENT_VALUES)}")
        if part in seen_agents:
            continue
        seen_agents.add(part)
        resolved_agents.append(part)
    return tuple(resolved_agents)


def choose_requested_mcp_names(*, locations: tuple[McpCatalogLocation, ...]) -> tuple[str, ...]:
    available_names = collect_available_mcp_names(locations=locations)
    selection = choose_from_options(
        options=available_names,
        msg="Choose MCP servers to install",
        multi=True,
        custom_input=False,
        header="MCP Servers",
        tv=True,
    )
    if selection is None or len(selection) == 0:
        raise ValueError("Selection cancelled for MCP servers")
    return tuple(selection)


def resolve_agent_launch_prefix(*, agent: AGENTS, repo_root: Path | None) -> list[str]:
    if repo_root is None:
        return []
    if agent == "cline":
        cline_dir = repo_root / ".cline"
        if cline_dir.is_dir():
            return ["--config", str(cline_dir)]
    return []


def install_resolved_mcp_servers(
    *,
    agent: AGENTS,
    scope: MCP_INSTALL_SCOPE,
    resolved_servers: tuple[ResolvedMcpServer, ...],
    repo_root: Path | None,
    home_dir: Path,
) -> Path:
    path = resolve_install_path(agent=agent, scope=scope, repo_root=repo_root, home_dir=home_dir)
    match agent:
        case "codex":
            _write_codex_config(path=path, resolved_servers=resolved_servers)
        case "copilot":
            _write_copilot_cli_config(path=path, resolved_servers=resolved_servers)
        case "claude" | "cursor-agent" | "forge" | "kilocode" | "warp-cli":
            _write_mcp_servers_file(path=path, resolved_servers=resolved_servers)
        case "gemini" | "qwen":
            _write_settings_with_mcp_servers(path=path, resolved_servers=resolved_servers, ensure_mcp_enabled=True)
        case "q" | "auggie" | "droid":
            _write_settings_with_mcp_servers(path=path, resolved_servers=resolved_servers, ensure_mcp_enabled=False)
        case "opencode":
            _write_opencode_config(path=path, resolved_servers=resolved_servers)
        case "cline":
            _write_cline_mcp_settings(path=path, resolved_servers=resolved_servers)
        case "crush":
            _write_crush_config(path=path, resolved_servers=resolved_servers)
        case "pi":
            _write_pi_mcp_adapter_config(path=path, resolved_servers=resolved_servers)
    return path


def resolve_install_path(
    *,
    agent: AGENTS,
    scope: MCP_INSTALL_SCOPE,
    repo_root: Path | None,
    home_dir: Path,
) -> Path:
    if scope == "local":
        if repo_root is None:
            raise ValueError("Local MCP installation requires running inside a git repository")
        match agent:
            case "codex":
                return repo_root / ".codex" / "config.toml"
            case "copilot":
                return repo_root / ".mcp.json"
            case "claude":
                return repo_root / ".mcp.json"
            case "forge":
                return repo_root / ".mcp.json"
            case "gemini":
                return repo_root / ".gemini" / "settings.json"
            case "cursor-agent":
                return repo_root / ".cursor" / "mcp.json"
            case "qwen":
                return repo_root / ".qwen" / "settings.json"
            case "q":
                return repo_root / ".amazonq" / "settings.json"
            case "opencode":
                return repo_root / ".opencode" / "opencode.jsonc"
            case "kilocode":
                return repo_root / ".kilocode" / "mcp.json"
            case "cline":
                return repo_root / ".cline" / "data" / "settings" / "cline_mcp_settings.json"
            case "auggie":
                return repo_root / ".augment" / "settings.json"
            case "warp-cli":
                return repo_root / ".warp" / "mcp.json"
            case "droid":
                return repo_root / ".factory" / "settings.json"
            case "crush":
                return repo_root / ".crush.json"
            case "pi":
                return repo_root / ".pi" / "mcp.json"

    match agent:
        case "codex":
            return home_dir / ".codex" / "config.toml"
        case "copilot":
            return _resolve_copilot_cli_user_config_path(home_dir=home_dir)
        case "claude":
            return home_dir / ".claude.json"
        case "forge":
            return home_dir / "forge" / ".mcp.json"
        case "gemini":
            return home_dir / ".gemini" / "settings.json"
        case "cursor-agent":
            return home_dir / ".cursor" / "mcp.json"
        case "qwen":
            return home_dir / ".qwen" / "settings.json"
        case "q":
            return home_dir / ".config" / "amazon-q" / "settings.json"
        case "opencode":
            return home_dir / ".config" / "opencode" / "opencode.jsonc"
        case "kilocode":
            return home_dir / ".config" / "kilocode" / "mcp.json"
        case "cline":
            return home_dir / ".cline" / "data" / "settings" / "cline_mcp_settings.json"
        case "auggie":
            return home_dir / ".augment" / "settings.json"
        case "warp-cli":
            if system() == "Darwin":
                return home_dir / "Library" / "Application Support" / "dev.warp.Warp-Stable" / "mcp.json"
            if system() == "Windows":
                return home_dir / "AppData" / "Roaming" / "Warp" / "mcp.json"
            return home_dir / ".local" / "share" / "warp" / "mcp.json"
        case "droid":
            return home_dir / ".factory" / "settings.json"
        case "crush":
            if system() == "Windows":
                return home_dir / "AppData" / "Local" / "crush" / "crush.json"
            return home_dir / ".config" / "crush" / "crush.json"
        case "pi":
            return home_dir / ".pi" / "agent" / "mcp.json"


def _resolve_copilot_cli_user_config_path(*, home_dir: Path) -> Path:
    copilot_home = os.environ.get("COPILOT_HOME")
    if copilot_home is not None and copilot_home.strip() != "":
        return Path(copilot_home).expanduser() / "mcp-config.json"
    return home_dir / ".copilot" / "mcp-config.json"


def _load_json_object(*, path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    if not path.is_file():
        raise ValueError(f"Config path exists but is not a file: {path}")
    raw_text = path.read_text(encoding="utf-8")
    if raw_text.strip() == "":
        return {}
    parsed: object = json.loads(remove_c_style_comments(raw_text))
    if not isinstance(parsed, dict):
        raise ValueError(f"Config file at {path} must contain a JSON object")
    return cast(dict[str, object], parsed)


def _write_json_object(*, path: Path, root: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(root, indent=2) + "\n", encoding="utf-8")


def _ensure_object_member(*, root: dict[str, object], key: str, path: Path) -> dict[str, object]:
    existing_value = root.get(key)
    if existing_value is None:
        created_value: dict[str, object] = {}
        root[key] = created_value
        return created_value
    if not isinstance(existing_value, dict):
        raise ValueError(f"Config field '{key}' in {path} must be a JSON object")
    return cast(dict[str, object], existing_value)


def _resolved_server_to_generic_entry(*, resolved_server: ResolvedMcpServer) -> dict[str, object]:
    definition = resolved_server["definition"]
    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a command")
        entry: dict[str, object] = {
            "command": command,
            "args": list(definition["args"]),
            "enabled": definition["enabled"],
        }
        if len(definition["env"]) > 0:
            entry["env"] = dict(definition["env"])
        if definition["cwd"] is not None:
            entry["cwd"] = definition["cwd"]
    else:
        url = definition["url"]
        if url is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a URL")
        entry = {
            "url": url,
            "enabled": definition["enabled"],
        }
        if len(definition["headers"]) > 0:
            entry["headers"] = dict(definition["headers"])
    if definition["description"] is not None:
        entry["description"] = definition["description"]
    return entry


def _write_mcp_servers_file(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    root = _load_json_object(path=path)
    mcp_servers = _ensure_object_member(root=root, key="mcpServers", path=path)
    for resolved_server in resolved_servers:
        mcp_servers[resolved_server["name"]] = _resolved_server_to_generic_entry(resolved_server=resolved_server)
    _write_json_object(path=path, root=root)


def _resolved_server_to_pi_entry(*, resolved_server: ResolvedMcpServer) -> dict[str, object]:
    definition = resolved_server["definition"]
    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a command")
        entry: dict[str, object] = {
            "command": command,
            "args": list(definition["args"]),
        }
        if len(definition["env"]) > 0:
            entry["env"] = dict(definition["env"])
        if definition["cwd"] is not None:
            entry["cwd"] = definition["cwd"]
    else:
        url = definition["url"]
        if url is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a URL")
        entry = {"url": url}
        if len(definition["headers"]) > 0:
            entry["headers"] = dict(definition["headers"])
    return entry


def _write_pi_mcp_adapter_config(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    root = _load_json_object(path=path)
    mcp_servers = _ensure_object_member(root=root, key="mcpServers", path=path)
    for resolved_server in resolved_servers:
        mcp_servers[resolved_server["name"]] = _resolved_server_to_pi_entry(resolved_server=resolved_server)
    _write_json_object(path=path, root=root)


def _write_settings_with_mcp_servers(
    *,
    path: Path,
    resolved_servers: tuple[ResolvedMcpServer, ...],
    ensure_mcp_enabled: bool,
) -> None:
    root = _load_json_object(path=path)
    mcp_servers = _ensure_object_member(root=root, key="mcpServers", path=path)
    for resolved_server in resolved_servers:
        mcp_servers[resolved_server["name"]] = _resolved_server_to_generic_entry(resolved_server=resolved_server)
    if ensure_mcp_enabled:
        mcp_settings = _ensure_object_member(root=root, key="mcp", path=path)
        mcp_settings["enabled"] = True
    _write_json_object(path=path, root=root)


def _resolved_server_to_copilot_cli_entry(*, resolved_server: ResolvedMcpServer) -> dict[str, object]:
    definition = resolved_server["definition"]
    tools: list[str] = ["*"] if definition["enabled"] else []
    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a command")
        entry: dict[str, object] = {
            "type": "local",
            "command": command,
            "args": list(definition["args"]),
            "tools": tools,
        }
        if len(definition["env"]) > 0:
            entry["env"] = dict(definition["env"])
        if definition["cwd"] is not None:
            entry["cwd"] = definition["cwd"]
        return entry

    url = definition["url"]
    if url is None:
        raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a URL")
    entry = {
        "type": "http",
        "url": url,
        "tools": tools,
    }
    if len(definition["headers"]) > 0:
        entry["headers"] = dict(definition["headers"])
    return entry


def _write_copilot_cli_config(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    root = _load_json_object(path=path)
    mcp_servers = _ensure_object_member(root=root, key="mcpServers", path=path)
    for resolved_server in resolved_servers:
        mcp_servers[resolved_server["name"]] = _resolved_server_to_copilot_cli_entry(resolved_server=resolved_server)
    _write_json_object(path=path, root=root)


def _resolved_server_to_cline_entry(*, resolved_server: ResolvedMcpServer) -> dict[str, object]:
    definition = resolved_server["definition"]
    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a command")
        entry: dict[str, object] = {
            "type": "stdio",
            "command": command,
            "args": list(definition["args"]),
        }
        if len(definition["env"]) > 0:
            entry["env"] = dict(definition["env"])
        if definition["cwd"] is not None:
            entry["cwd"] = definition["cwd"]
    else:
        url = definition["url"]
        if url is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a URL")
        entry = {
            "type": "streamableHttp",
            "url": url,
        }
        if len(definition["headers"]) > 0:
            entry["headers"] = dict(definition["headers"])
    if not definition["enabled"]:
        entry["disabled"] = True
    return entry


def _write_cline_mcp_settings(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    root = _load_json_object(path=path)
    mcp_servers = _ensure_object_member(root=root, key="mcpServers", path=path)
    for resolved_server in resolved_servers:
        mcp_servers[resolved_server["name"]] = _resolved_server_to_cline_entry(resolved_server=resolved_server)
    _write_json_object(path=path, root=root)


def _resolved_server_to_opencode_entry(*, resolved_server: ResolvedMcpServer) -> dict[str, object]:
    definition = resolved_server["definition"]
    if definition["cwd"] is not None:
        raise ValueError(f"OpenCode MCP config does not support 'cwd' for server '{resolved_server['name']}'")
    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a command")
        entry: dict[str, object] = {
            "type": "local",
            "command": [command, *definition["args"]],
            "enabled": definition["enabled"],
        }
        if len(definition["env"]) > 0:
            entry["environment"] = dict(definition["env"])
        return entry

    url = definition["url"]
    if url is None:
        raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a URL")
    entry = {
        "type": "remote",
        "url": url,
        "enabled": definition["enabled"],
    }
    if len(definition["headers"]) > 0:
        entry["headers"] = dict(definition["headers"])
    return entry


def _write_opencode_config(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    root = _load_json_object(path=path)
    mcp = _ensure_object_member(root=root, key="mcp", path=path)
    for resolved_server in resolved_servers:
        mcp[resolved_server["name"]] = _resolved_server_to_opencode_entry(resolved_server=resolved_server)
    _write_json_object(path=path, root=root)


def _resolved_server_to_crush_entry(*, resolved_server: ResolvedMcpServer) -> dict[str, object]:
    definition = resolved_server["definition"]
    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a command")
        entry: dict[str, object] = {
            "type": "stdio",
            "command": command,
            "args": list(definition["args"]),
        }
        if len(definition["env"]) > 0:
            entry["env"] = dict(definition["env"])
        if definition["cwd"] is not None:
            entry["cwd"] = definition["cwd"]
        return entry

    url = definition["url"]
    if url is None:
        raise ValueError(f"Resolved MCP server '{resolved_server['name']}' is missing a URL")
    entry = {
        "type": "http",
        "url": url,
    }
    if len(definition["headers"]) > 0:
        entry["headers"] = dict(definition["headers"])
    return entry


def _write_crush_config(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    root = _load_json_object(path=path)
    mcp = _ensure_object_member(root=root, key="mcp", path=path)
    for resolved_server in resolved_servers:
        mcp[resolved_server["name"]] = _resolved_server_to_crush_entry(resolved_server=resolved_server)
    _write_json_object(path=path, root=root)


def _write_codex_config(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    if path.exists() and not path.is_file():
        raise ValueError(f"Config path exists but is not a file: {path}")

    existing_text = path.read_text(encoding="utf-8") if path.exists() else ""
    updated_text = existing_text
    for resolved_server in resolved_servers:
        updated_text = _remove_codex_server_block(text=updated_text, server_name=resolved_server["name"])
    updated_text = updated_text.rstrip()

    rendered_blocks = [_render_codex_server_block(resolved_server=resolved_server) for resolved_server in resolved_servers]
    combined_blocks = "\n\n".join(rendered_blocks)

    if updated_text == "":
        final_text = combined_blocks + "\n"
    else:
        final_text = updated_text + "\n\n" + combined_blocks + "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(final_text, encoding="utf-8")


def _remove_codex_server_block(*, text: str, server_name: str) -> str:
    escaped_name = re.escape(server_name)
    pattern = re.compile(
        rf"""(?ms)^\[mcp_servers\.{escaped_name}\]\n.*?(?=^\[(?!mcp_servers\.{escaped_name}\.)|\Z)"""
    )
    return pattern.sub("", text)


def _render_codex_server_block(*, resolved_server: ResolvedMcpServer) -> str:
    name = resolved_server["name"]
    definition = resolved_server["definition"]
    lines = [f"[mcp_servers.{name}]"]

    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"Resolved MCP server '{name}' is missing a command")
        lines.append(f"""command = {json.dumps(command)}""")
        lines.append(f"""args = {json.dumps(definition["args"])}""")
        if len(definition["env"]) > 0:
            lines.append("")
            lines.append(f"[mcp_servers.{name}.env]")
            for env_key, env_value in definition["env"].items():
                lines.append(f"""{env_key} = {json.dumps(env_value)}""")
        return "\n".join(lines)

    url = definition["url"]
    if url is None:
        raise ValueError(f"Resolved MCP server '{name}' is missing a URL")
    lines.append(f"""url = {json.dumps(url)}""")
    if len(definition["headers"]) > 0:
        bearer_token_env_var = _extract_bearer_token_env_var(headers=definition["headers"], server_name=name)
        lines.append(f"""bearer_token_env_var = {json.dumps(bearer_token_env_var)}""")
    return "\n".join(lines)


def _extract_bearer_token_env_var(*, headers: dict[str, str], server_name: str) -> str:
    if len(headers) != 1 or "Authorization" not in headers:
        raise ValueError(
            f"Codex MCP config only supports bearer-token HTTP auth. Unsupported headers for server '{server_name}': {', '.join(headers)}"
        )
    authorization_value = headers["Authorization"]
    match = _AUTHORIZATION_BEARER_ENV_PATTERN.match(authorization_value)
    if match is None:
        raise ValueError(
            f"Codex MCP config only supports Authorization headers of the form 'Bearer $ENV_VAR' for server '{server_name}'"
        )
    braced_name = match.group("braced")
    plain_name = match.group("plain")
    bearer_token_env_var = braced_name if braced_name is not None else plain_name
    if bearer_token_env_var is None:
        raise ValueError(f"Failed to resolve bearer token env var for server '{server_name}'")
    return bearer_token_env_var
