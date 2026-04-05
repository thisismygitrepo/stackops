import json
from pathlib import Path
from typing import get_args
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python import agents
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS
from machineconfig.scripts.python.helpers.helpers_agents.mcp_install import install_resolved_mcp_servers
from machineconfig.scripts.python.helpers.helpers_agents.mcp_catalog import (
    format_resolved_mcp_servers,
    parse_requested_mcp_names,
    resolve_requested_mcp_servers,
)
from machineconfig.scripts.python.helpers.helpers_agents.mcp_types import ResolvedMcpServer


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
    assert "--agent" in result.output
    assert "-a" in result.output
    assert "--scope" in result.output
    assert "-s" in result.output
    assert "--where" in result.output
    assert "-w" in result.output
    assert "--edit" in result.output
    assert "-e" in result.output
    assert "REQUESTED_MCP_SERVERS" in result.output


def test_add_mcp_command_installs_servers_for_selected_agent(tmp_path: Path) -> None:
    private_catalog = tmp_path / "private" / "mcp.json"
    public_catalog = tmp_path / "public" / "mcp.json"

    _write_mcp_catalog(private_catalog, {"mcpServers": {"github": {"command": "uvx", "args": ["mcp-github-private"]}}})
    _write_mcp_catalog(public_catalog, {"mcpServers": {"context7": {"url": "https://mcp.context7.com/mcp"}}})

    with (
        patch(
            "machineconfig.scripts.python.helpers.helpers_agents.mcp_catalog.default_mcp_catalog_locations",
            return_value=(
                {"scope": "private", "path": private_catalog},
                {"scope": "public", "path": public_catalog},
                {"scope": "library", "path": tmp_path / "library" / "mcp.json"},
            ),
        ),
        patch("machineconfig.utils.accessories.get_repo_root", return_value=tmp_path),
    ):
        result = runner.invoke(agents.get_app(), ["m", "github,context7", "--agent", "codex", "--scope", "local"])

    assert result.exit_code == 0
    codex_config_path = tmp_path / ".codex" / "config.toml"
    assert codex_config_path.read_text(encoding="utf-8") == (
        "[mcp_servers.github]\n"
        'command = "uvx"\n'
        'args = ["mcp-github-private"]\n'
        "\n"
        "[mcp_servers.context7]\n"
        'url = "https://mcp.context7.com/mcp"\n'
    )
    assert "Installing: github (private), context7 (public)" in result.stdout
    assert f"codex: {codex_config_path}" in result.stdout


def test_add_mcp_without_argument_uses_interactive_picker(tmp_path: Path) -> None:
    public_catalog = tmp_path / "public" / "mcp.json"
    _write_mcp_catalog(
        public_catalog,
        {
            "mcpServers": {
                "context7": {"url": "https://mcp.context7.com/mcp"},
                "filesystem": {"command": "uvx", "args": ["mcp-filesystem"]},
            }
        },
    )

    with (
        patch(
            "machineconfig.scripts.python.helpers.helpers_agents.mcp_catalog.default_mcp_catalog_locations",
            return_value=(
                {"scope": "private", "path": tmp_path / "private" / "mcp.json"},
                {"scope": "public", "path": public_catalog},
                {"scope": "library", "path": tmp_path / "library" / "mcp.json"},
            ),
        ),
        patch("machineconfig.utils.accessories.get_repo_root", return_value=tmp_path),
        patch(
            "machineconfig.scripts.python.helpers.helpers_agents.mcp_install.choose_from_options",
            return_value=["context7"],
        ),
    ):
        result = runner.invoke(agents.get_app(), ["m", "--agent", "copilot", "--scope", "local"])

    assert result.exit_code == 0
    copilot_config_path = tmp_path / ".vscode" / "mcp.json"
    assert json.loads(copilot_config_path.read_text(encoding="utf-8")) == {
        "servers": {
            "context7": {
                "type": "http",
                "url": "https://mcp.context7.com/mcp",
            }
        }
    }
    assert f"copilot: {copilot_config_path}" in result.stdout


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


@pytest.mark.parametrize(
    ("agent", "expected_relative_path"),
    [
        ("cursor-agent", Path(".cursor/mcp.json")),
        ("gemini", Path(".gemini/settings.json")),
        ("claude", Path(".mcp.json")),
        ("qwen", Path(".qwen/settings.json")),
        ("copilot", Path(".vscode/mcp.json")),
        ("codex", Path(".codex/config.toml")),
        ("forge", Path(".mcp.json")),
        ("crush", Path(".crush.json")),
        ("q", Path(".amazonq/settings.json")),
        ("opencode", Path(".opencode/opencode.jsonc")),
        ("kilocode", Path(".kilocode/mcp.json")),
        ("cline", Path(".cline/data/settings/cline_mcp_settings.json")),
        ("auggie", Path(".augment/settings.json")),
        ("warp-cli", Path(".warp/mcp.json")),
        ("droid", Path(".factory/settings.json")),
    ],
)
def test_install_resolved_mcp_servers_supports_every_agent(agent: AGENTS, expected_relative_path: Path, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    home_dir = tmp_path / "home"
    repo_root.mkdir()
    home_dir.mkdir()

    resolved_servers: tuple[ResolvedMcpServer, ...] = (
        {
            "name": "context7",
            "scope": "public",
            "source_path": tmp_path / "catalog.json",
            "definition": {
                "transport": "http",
                "command": None,
                "args": [],
                "env": {},
                "url": "https://mcp.context7.com/mcp",
                "headers": {},
                "cwd": None,
                "description": None,
                "enabled": True,
            },
        },
    )

    install_path = install_resolved_mcp_servers(
        agent=agent,
        scope="local",
        resolved_servers=resolved_servers,
        repo_root=repo_root,
        home_dir=home_dir,
    )

    assert install_path == repo_root / expected_relative_path
    assert install_path.exists()
    if agent == "codex":
        assert "[mcp_servers.context7]" in install_path.read_text(encoding="utf-8")
        return

    installed_config = json.loads(install_path.read_text(encoding="utf-8"))
    if agent == "copilot":
        assert installed_config["servers"]["context7"]["url"] == "https://mcp.context7.com/mcp"
        return
    if agent == "opencode":
        assert installed_config["mcp"]["context7"]["url"] == "https://mcp.context7.com/mcp"
        return
    if agent == "crush":
        assert installed_config["mcp"]["context7"]["url"] == "https://mcp.context7.com/mcp"
        return
    assert "mcpServers" in installed_config
    assert installed_config["mcpServers"]["context7"]["url"] == "https://mcp.context7.com/mcp"


def test_build_agent_command_uses_repo_local_cline_config(tmp_path: Path) -> None:
    from machineconfig.scripts.python.helpers.helpers_agents.agents_run_impl import build_agent_command

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".cline").mkdir()
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("hello", encoding="utf-8")

    with patch(
        "machineconfig.scripts.python.helpers.helpers_agents.agents_run_impl.get_repo_root",
        return_value=repo_root,
    ):
        command = build_agent_command(agent="cline", prompt_file=prompt_path, reasoning_effort=None)

    assert f"--config {repo_root / '.cline'}" in command


def test_agent_enum_test_matrix_stays_in_sync() -> None:
    tested_agents = {
        "cursor-agent",
        "gemini",
        "claude",
        "qwen",
        "copilot",
        "codex",
        "forge",
        "crush",
        "q",
        "opencode",
        "kilocode",
        "cline",
        "auggie",
        "warp-cli",
        "droid",
    }
    assert tested_agents == set(get_args(AGENTS))
