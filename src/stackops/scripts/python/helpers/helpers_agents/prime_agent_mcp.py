import json
from pathlib import Path
import re
from typing import Final, cast

from stackops.scripts.python.helpers.helpers_agents.mcp_types import ResolvedMcpServer

_ENV_REFERENCE: Final[str] = r"""\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|(?P<plain>[A-Za-z_][A-Za-z0-9_]*))"""
_ENV_REFERENCE_PATTERN: Final[re.Pattern[str]] = re.compile(rf"""^{_ENV_REFERENCE}$""")
_BEARER_ENV_REFERENCE_PATTERN: Final[re.Pattern[str]] = re.compile(rf"""^Bearer\s+{_ENV_REFERENCE}$""")


def _referenced_env_name(*, pattern: re.Pattern[str], value: str) -> str | None:
    match = pattern.match(value)
    if match is None:
        return None
    return cast(str, match.group("braced") or match.group("plain"))


def _prime_agent_entry(*, resolved_server: ResolvedMcpServer) -> dict[str, object]:
    name = resolved_server["name"]
    definition = resolved_server["definition"]
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", name) is None:
        raise ValueError(f"""prime-agent MCP server names must start with a letter or digit and contain at most 64 letters, digits, '_' or '-': {name}""")
    if not definition["enabled"]:
        raise ValueError(f"""prime-agent has no per-server enabled flag; refusing to install disabled MCP server '{name}'""")
    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"""Resolved MCP server '{name}' is missing a command""")
        entry: dict[str, object] = {"type": "stdio", "command": command}
        if definition["args"]:
            entry["args"] = list(definition["args"])
        if definition["cwd"] is not None:
            entry["cwd"] = definition["cwd"]
        environment: dict[str, dict[str, str]] = {}
        for child_name, value in definition["env"].items():
            source_name = _referenced_env_name(pattern=_ENV_REFERENCE_PATTERN, value=value)
            if source_name is None:
                raise ValueError(
                    f"""prime-agent only forwards environment variables by reference; set '{child_name}' for MCP server '{name}' to '$SOURCE_VAR'"""
                )
            environment[child_name] = {"env": source_name}
        if environment:
            entry["env"] = environment
        return entry
    url = definition["url"]
    if url is None:
        raise ValueError(f"""Resolved MCP server '{name}' is missing a URL""")
    entry = {"type": "http", "url": url}
    headers = definition["headers"]
    if headers:
        token_name = _referenced_env_name(pattern=_BEARER_ENV_REFERENCE_PATTERN, value=headers.get("Authorization", ""))
        if len(headers) != 1 or token_name is None:
            raise ValueError(
                f"""prime-agent HTTP MCP servers only support an 'Authorization: Bearer $ENV_VAR' header; unsupported headers for '{name}': {", ".join(headers)}"""
            )
        entry["bearerTokenEnvVar"] = token_name
    return entry


def write_prime_agent_mcp_config(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    root: dict[str, object] = {}
    if path.is_file() and path.read_text(encoding="utf-8").strip():
        parsed: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError(f"""prime-agent settings must contain a JSON object: {path}""")
        root = cast(dict[str, object], parsed)
    raw_servers = root.get("mcpServers")
    if raw_servers is None:
        raw_servers = {}
        root["mcpServers"] = raw_servers
    if not isinstance(raw_servers, dict):
        raise ValueError(f"""prime-agent setting 'mcpServers' must be a JSON object: {path}""")
    servers = cast(dict[str, object], raw_servers)
    for resolved_server in resolved_servers:
        servers[resolved_server["name"]] = _prime_agent_entry(resolved_server=resolved_server)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(root, indent=2) + "\n", encoding="utf-8")
