from collections.abc import MutableMapping
from pathlib import Path
import re
from typing import cast

import tomlkit

from stackops.scripts.python.helpers.helpers_agents.mcp_types import ResolvedMcpServer


def write_maki_mcp_config(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    document = tomlkit.parse(path.read_text(encoding="utf-8")) if path.exists() else tomlkit.document()
    if "mcp" not in document:
        document["mcp"] = tomlkit.table()
    raw_servers = document["mcp"]
    if not isinstance(raw_servers, MutableMapping):
        raise ValueError(f"""Maki MCP configuration must contain an mcp table: {path}""")
    servers = cast(MutableMapping[str, object], raw_servers)
    for server in resolved_servers:
        name = server["name"]
        if re.fullmatch(r"[A-Za-z0-9-]{1,64}", name) is None:
            raise ValueError(f"""Maki MCP server names must contain 1–64 letters, digits or hyphens: {name}""")
        definition = server["definition"]
        if definition["cwd"] is not None:
            raise ValueError(f"""Maki MCP server '{name}' does not support cwd""")
        entry: dict[str, object] = {"enabled": definition["enabled"]}
        if definition["transport"] == "stdio":
            command = definition["command"]
            if command is None:
                raise ValueError(f"""Maki MCP server '{name}' is missing a command""")
            entry["command"] = [command, *definition["args"]]
            if definition["env"]:
                entry["environment"] = dict(definition["env"])
        else:
            url = definition["url"]
            if url is None:
                raise ValueError(f"""Maki MCP server '{name}' is missing a URL""")
            entry["url"] = url
            if definition["headers"]:
                entry["headers"] = dict(definition["headers"])
        servers[name] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomlkit.dumps(document), encoding="utf-8")
