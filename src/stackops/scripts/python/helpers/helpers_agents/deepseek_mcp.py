from collections.abc import Iterator
from pathlib import Path
import re

import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from stackops.scripts.python.helpers.helpers_agents.mcp_types import ResolvedMcpServer


def _mapping_fields(node: MappingNode) -> dict[str, Node]:
    fields: dict[str, Node] = {}
    for key, value in node.value:
        if not isinstance(key, ScalarNode) or key.tag not in {"tag:yaml.org,2002:str", "tag:yaml.org,2002:merge"}:
            raise ValueError("DeepSeek configuration keys must be strings")
        fields[key.value] = value
    return fields


def _patch_rows(root: SequenceNode) -> Iterator[MappingNode]:
    for patch in root.value:
        if not isinstance(patch, MappingNode):
            raise ValueError("DeepSeek configuration patches must be mappings")
        yield patch
        inserted = _mapping_fields(patch).get("insert")
        if inserted is None:
            continue
        if not isinstance(inserted, SequenceNode):
            raise ValueError("DeepSeek insert patches must contain a list of plugin rows")
        for row in inserted.value:
            if not isinstance(row, MappingNode):
                raise ValueError("DeepSeek inserted plugin rows must be mappings")
            yield row


def _server_row(server: ResolvedMcpServer) -> MappingNode:
    name = server["name"]
    if re.fullmatch(r"[A-Za-z0-9_-]{1,32}", name) is None:
        raise ValueError(f"""DeepSeek MCP server name must contain 1–32 letters, digits, underscores or hyphens: {name}""")
    definition = server["definition"]
    config: dict[str, object] = {"serverName": name}
    if definition["transport"] == "stdio":
        command = definition["command"]
        if command is None:
            raise ValueError(f"""DeepSeek MCP server '{name}' is missing a command""")
        config.update({"transport": "stdio", "command": command, "args": definition["args"]})
        if definition["env"]:
            config["env"] = definition["env"]
        if definition["cwd"] is not None:
            config["cwd"] = definition["cwd"]
    else:
        url = definition["url"]
        if url is None:
            raise ValueError(f"""DeepSeek MCP server '{name}' is missing a URL""")
        config.update({"transport": "streamable-http", "url": url})
        if definition["headers"]:
            config["headers"] = definition["headers"]
    node = yaml.compose(yaml.safe_dump({
        "id": f"""mcp-{name}""",
        "name": "@deepseek-ai/dsh-mcp-client",
        "disabled": not definition["enabled"],
        "config": config,
    }, sort_keys=False))
    if not isinstance(node, MappingNode):
        raise ValueError("Unable to render DeepSeek MCP configuration")
    return node


def write_deepseek_mcp_config(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
    if path.exists() and not path.is_file():
        raise ValueError(f"""Config path exists but is not a file: {path}""")
    root = yaml.compose(path.read_text(encoding="utf-8")) if path.exists() else None
    if root is None:
        root = SequenceNode("tag:yaml.org,2002:seq", [])
    if not isinstance(root, SequenceNode):
        raise ValueError(f"""DeepSeek configuration must be a YAML patch list: {path}""")
    for server in resolved_servers:
        replacement = _server_row(server)
        replacement_fields = _mapping_fields(replacement)
        target_id = f"""mcp-{server['name']}"""
        rows = list(_patch_rows(root))
        for row in rows:
            fields = _mapping_fields(row)
            plugin_name = fields.get("name")
            config = fields.get("config")
            if not isinstance(plugin_name, ScalarNode) or plugin_name.value != "@deepseek-ai/dsh-mcp-client":
                continue
            configured_name = _mapping_fields(config).get("serverName") if isinstance(config, MappingNode) else None
            row_id = fields.get("id")
            if isinstance(configured_name, ScalarNode) and configured_name.value == server["name"] and isinstance(row_id, ScalarNode):
                target_id = row_id.value
        found = False
        for row in rows:
            fields = _mapping_fields(row)
            row_id = fields.get("id")
            if not isinstance(row_id, ScalarNode) or row_id.value != target_id:
                continue
            plugin_name = fields.get("name")
            if isinstance(plugin_name, ScalarNode) and plugin_name.value != "@deepseek-ai/dsh-mcp-client":
                raise ValueError(f"""DeepSeek plugin id '{target_id}' belongs to another plugin in {path}""")
            row.value = [(key, value) for key, value in row.value if isinstance(key, ScalarNode) and key.value not in {"config", "disabled"}]
            row.value.extend((ScalarNode("tag:yaml.org,2002:str", key), replacement_fields[key]) for key in ("disabled", "config"))
            found = True
        if not found:
            root.value.append(MappingNode("tag:yaml.org,2002:map", [
                (ScalarNode("tag:yaml.org,2002:str", "insert"), SequenceNode("tag:yaml.org,2002:seq", [replacement])),
            ]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.serialize(root), encoding="utf-8")
