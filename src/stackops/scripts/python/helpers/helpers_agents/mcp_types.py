from pathlib import Path
from typing import Literal, TypeAlias, TypedDict


MCP_CATALOG_SCOPE: TypeAlias = Literal["repo", "private", "public", "library"]
MCP_CATALOG_WHERE: TypeAlias = Literal["all", "a", "repo", "r", "private", "p", "public", "b", "library", "l"]
MCP_TRANSPORT: TypeAlias = Literal["stdio", "http"]


class McpCatalogLocation(TypedDict):
    scope: MCP_CATALOG_SCOPE
    path: Path


class McpServerDefinitionRaw(TypedDict, total=False):
    command: str
    args: list[str]
    env: dict[str, str]
    url: str
    headers: dict[str, str]
    cwd: str
    description: str
    enabled: bool


class McpCatalogFile(TypedDict):
    mcpServers: dict[str, McpServerDefinitionRaw]


class ResolvedMcpServerDefinition(TypedDict):
    transport: MCP_TRANSPORT
    command: str | None
    args: list[str]
    env: dict[str, str]
    url: str | None
    headers: dict[str, str]
    cwd: str | None
    description: str | None
    enabled: bool


class ResolvedMcpServer(TypedDict):
    name: str
    scope: MCP_CATALOG_SCOPE
    source_path: Path
    definition: ResolvedMcpServerDefinition
