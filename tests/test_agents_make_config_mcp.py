import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from machineconfig.scripts.python import agents
from machineconfig.scripts.python.helpers.helpers_agents.mcp_catalog import (
    format_resolved_mcp_servers,
    parse_requested_mcp_names,
    resolve_requested_mcp_servers,
)


runner = CliRunner()


def _write_mcp_catalog(path: Path, content: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, indent=2), encoding="utf-8")


def test_make_config_help_no_longer_lists_add_mcp_option() -> None:
    result = runner.invoke(agents.get_app(), ["g", "--help"])

    assert result.exit_code == 0
    assert "--add-mcp" not in result.output


def test_add_mcp_help_lists_edit_and_where_options() -> None:
    result = runner.invoke(agents.get_app(), ["m", "--help"])

    assert result.exit_code == 0
    assert "--where" in result.output
    assert "-w" in result.output
    assert "--edit" in result.output
    assert "-e" in result.output
    assert "REQUESTED_MCP_SERVERS" in result.output


def test_add_mcp_command_resolves_servers_using_selected_locations(tmp_path: Path) -> None:
    private_catalog = tmp_path / "private" / "mcp.json"
    public_catalog = tmp_path / "public" / "mcp.json"

    _write_mcp_catalog(private_catalog, {"mcpServers": {"github": {"command": "uvx", "args": ["mcp-github-private"]}}})
    _write_mcp_catalog(public_catalog, {"mcpServers": {"context7": {"url": "https://mcp.context7.com/mcp"}}})

    with patch(
        "machineconfig.scripts.python.helpers.helpers_agents.mcp_catalog.default_mcp_catalog_locations",
        return_value=(
            {"scope": "private", "path": private_catalog},
            {"scope": "public", "path": public_catalog},
            {"scope": "library", "path": tmp_path / "library" / "mcp.json"},
        )
    ):
        result = runner.invoke(agents.get_app(), ["m", "github,context7"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "github (private), context7 (public)"


def test_add_mcp_edit_scaffolds_missing_public_catalog_before_opening(tmp_path: Path) -> None:
    public_catalog = tmp_path / "public" / "mcp.json"
    edited_paths: list[Path] = []

    def _capture_edit(path: Path) -> None:
        edited_paths.append(path)

    with (
        patch(
            "machineconfig.scripts.python.helpers.helpers_agents.mcp_catalog.default_mcp_catalog_locations",
            return_value=(
                {"scope": "private", "path": tmp_path / "private" / "mcp.json"},
                {"scope": "public", "path": public_catalog},
                {"scope": "library", "path": tmp_path / "library" / "mcp.json"},
            ),
        ),
        patch("machineconfig.scripts.python.helpers.helpers_agents.mcp_catalog.edit_mcp_catalog", side_effect=_capture_edit),
    ):
        result = runner.invoke(agents.get_app(), ["m", "--where", "public", "--edit"])

    assert result.exit_code == 0
    assert json.loads(public_catalog.read_text(encoding="utf-8")) == {"mcpServers": {}}
    assert edited_paths == [public_catalog]


def test_parse_requested_mcp_names_rejects_duplicates() -> None:
    try:
        parse_requested_mcp_names("github,context7,github")
    except ValueError as error:
        assert str(error) == "Duplicate MCP server names are not allowed: github"
    else:
        raise AssertionError("Expected duplicate MCP names to fail")


def test_resolve_requested_mcp_servers_prefers_private_then_public_then_library(tmp_path: Path) -> None:
    private_catalog = tmp_path / "private" / "mcp.json"
    public_catalog = tmp_path / "public" / "mcp.json"
    library_catalog = tmp_path / "library" / "mcp.json"

    _write_mcp_catalog(
        private_catalog,
        {"mcpServers": {"github": {"command": "uvx", "args": ["mcp-github-private"], "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}}}},
    )
    _write_mcp_catalog(
        public_catalog,
        {"mcpServers": {"github": {"command": "uvx", "args": ["mcp-github-public"]}, "context7": {"url": "https://mcp.context7.com/mcp"}}},
    )
    _write_mcp_catalog(
        library_catalog,
        {"mcpServers": {"filesystem": {"command": "uvx", "args": ["mcp-filesystem"]}}},
    )

    resolved_servers = resolve_requested_mcp_servers(
        ("github", "context7", "filesystem"),
        locations=(
            {"scope": "private", "path": private_catalog},
            {"scope": "public", "path": public_catalog},
            {"scope": "library", "path": library_catalog},
        ),
    )

    assert [resolved_server["name"] for resolved_server in resolved_servers] == ["github", "context7", "filesystem"]
    assert [resolved_server["scope"] for resolved_server in resolved_servers] == ["private", "public", "library"]
    assert resolved_servers[0]["definition"] == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-github-private"],
        "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
        "url": None,
        "headers": {},
        "cwd": None,
        "description": None,
        "enabled": True,
    }
    assert resolved_servers[1]["definition"] == {
        "transport": "http",
        "command": None,
        "args": [],
        "env": {},
        "url": "https://mcp.context7.com/mcp",
        "headers": {},
        "cwd": None,
        "description": None,
        "enabled": True,
    }
    assert format_resolved_mcp_servers(resolved_servers) == "github (private), context7 (public), filesystem (library)"


def test_resolve_requested_mcp_servers_rejects_missing_server(tmp_path: Path) -> None:
    public_catalog = tmp_path / "public" / "mcp.json"
    _write_mcp_catalog(public_catalog, {"mcpServers": {"context7": {"url": "https://mcp.context7.com/mcp"}}})

    try:
        resolve_requested_mcp_servers(
            ("github",),
            locations=({"scope": "public", "path": public_catalog},),
        )
    except ValueError as error:
        assert str(error) == f"MCP servers not found: github. Searched: {public_catalog}"
    else:
        raise AssertionError("Expected missing MCP server to fail")
