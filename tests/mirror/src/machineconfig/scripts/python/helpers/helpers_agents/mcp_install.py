from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from machineconfig.scripts.python.helpers.helpers_agents import mcp_install as module
from machineconfig.scripts.python.helpers.helpers_agents.mcp_types import McpCatalogLocation, ResolvedMcpServer


def _read_json_object(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _stdio_server(name: str, enabled: bool, cwd: str | None, description: str | None) -> ResolvedMcpServer:
    return {
        "name": name,
        "scope": "public",
        "source_path": Path("/catalog.json"),
        "definition": {
            "transport": "stdio",
            "command": "uvx",
            "args": ["serve"],
            "env": {"TOKEN": "value"},
            "url": None,
            "headers": {},
            "cwd": cwd,
            "description": description,
            "enabled": enabled,
        },
    }


def _http_server(name: str, enabled: bool, headers: dict[str, str], description: str | None) -> ResolvedMcpServer:
    return {
        "name": name,
        "scope": "public",
        "source_path": Path("/catalog.json"),
        "definition": {
            "transport": "http",
            "command": None,
            "args": [],
            "env": {},
            "url": f"https://example.com/{name}",
            "headers": headers,
            "cwd": None,
            "description": description,
            "enabled": enabled,
        },
    }


def test_parse_requested_agents_blank_means_all_and_duplicates_collapse() -> None:
    assert module.parse_requested_agents("") == module._AGENT_VALUES
    assert module.parse_requested_agents("codex, qwen, codex") == ("codex", "qwen")


@pytest.mark.parametrize(
    ("raw_value", "message"),
    [
        ("codex,,qwen", "without empty entries"),
        ("codex,unknown", "Unsupported agent: unknown"),
    ],
)
def test_parse_requested_agents_rejects_invalid_values(raw_value: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        module.parse_requested_agents(raw_value)


def test_choose_requested_mcp_names_returns_picker_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locations: tuple[McpCatalogLocation, ...] = ({"scope": "public", "path": tmp_path / "mcp.json"},)

    def fake_collect_available_mcp_names(*, locations: tuple[McpCatalogLocation, ...]) -> tuple[str, ...]:
        assert len(locations) == 1
        return ("alpha", "beta")

    def fake_choose_from_options(
        *,
        options: tuple[str, ...],
        msg: str,
        multi: bool,
        custom_input: bool,
        header: str,
        tv: bool,
    ) -> tuple[str, ...] | None:
        assert options == ("alpha", "beta")
        assert msg == "Choose MCP servers to install"
        assert multi is True
        assert custom_input is False
        assert header == "MCP Servers"
        assert tv is True
        return ("beta",)

    monkeypatch.setattr(module, "collect_available_mcp_names", fake_collect_available_mcp_names)
    monkeypatch.setattr(module, "choose_from_options", fake_choose_from_options)

    assert module.choose_requested_mcp_names(locations=locations) == ("beta",)


def test_choose_requested_mcp_names_rejects_cancelled_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locations: tuple[McpCatalogLocation, ...] = ({"scope": "public", "path": tmp_path / "mcp.json"},)

    def fake_collect_available_mcp_names(*, locations: tuple[McpCatalogLocation, ...]) -> tuple[str, ...]:
        assert len(locations) == 1
        return ("alpha",)

    def fake_choose_from_options(
        *,
        options: tuple[str, ...],
        msg: str,
        multi: bool,
        custom_input: bool,
        header: str,
        tv: bool,
    ) -> tuple[str, ...] | None:
        return None

    monkeypatch.setattr(module, "collect_available_mcp_names", fake_collect_available_mcp_names)
    monkeypatch.setattr(module, "choose_from_options", fake_choose_from_options)

    with pytest.raises(ValueError, match="Selection cancelled"):
        module.choose_requested_mcp_names(locations=locations)


def test_resolve_agent_launch_prefix_uses_repo_cline_directory_only_when_present(tmp_path: Path) -> None:
    assert module.resolve_agent_launch_prefix(agent="cline", repo_root=tmp_path) == []
    assert module.resolve_agent_launch_prefix(agent="codex", repo_root=tmp_path) == []
    assert module.resolve_agent_launch_prefix(agent="cline", repo_root=None) == []

    (tmp_path / ".cline").mkdir()

    assert module.resolve_agent_launch_prefix(agent="cline", repo_root=tmp_path) == [
        "--config",
        str(tmp_path / ".cline"),
    ]


@pytest.mark.parametrize(
    ("agent", "expected_relative_path"),
    [
        ("codex", Path(".codex/config.toml")),
        ("copilot", Path(".vscode/mcp.json")),
        ("claude", Path(".mcp.json")),
        ("forge", Path(".mcp.json")),
        ("gemini", Path(".gemini/settings.json")),
        ("cursor-agent", Path(".cursor/mcp.json")),
        ("qwen", Path(".qwen/settings.json")),
        ("q", Path(".amazonq/settings.json")),
        ("opencode", Path(".opencode/opencode.jsonc")),
        ("kilocode", Path(".kilocode/mcp.json")),
        ("cline", Path(".cline/data/settings/cline_mcp_settings.json")),
        ("auggie", Path(".augment/settings.json")),
        ("warp-cli", Path(".warp/mcp.json")),
        ("droid", Path(".factory/settings.json")),
        ("crush", Path(".crush.json")),
    ],
)
def test_resolve_install_path_local_layout(
    agent: str,
    expected_relative_path: Path,
    tmp_path: Path,
) -> None:
    home_dir = tmp_path / "home"

    assert (
        module.resolve_install_path(agent=agent, scope="local", repo_root=tmp_path, home_dir=home_dir)
        == tmp_path / expected_relative_path
    )


def test_resolve_install_path_local_requires_repository_context(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires running inside a git repository"):
        module.resolve_install_path(agent="codex", scope="local", repo_root=None, home_dir=tmp_path)


@pytest.mark.parametrize(
    ("agent", "expected_relative_path"),
    [
        ("codex", Path(".codex/config.toml")),
        ("copilot", Path(".copilot/mcp-config.json")),
        ("claude", Path(".claude.json")),
        ("forge", Path("forge/.mcp.json")),
        ("gemini", Path(".gemini/settings.json")),
        ("cursor-agent", Path(".cursor/mcp.json")),
        ("qwen", Path(".qwen/settings.json")),
        ("q", Path(".config/amazon-q/settings.json")),
        ("opencode", Path(".config/opencode/opencode.jsonc")),
        ("kilocode", Path(".config/kilocode/mcp.json")),
        ("cline", Path(".cline/data/settings/cline_mcp_settings.json")),
        ("auggie", Path(".augment/settings.json")),
        ("warp-cli", Path(".local/share/warp/mcp.json")),
        ("droid", Path(".factory/settings.json")),
        ("crush", Path(".config/crush/crush.json")),
    ],
)
def test_resolve_install_path_global_linux_layout(
    agent: str,
    expected_relative_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_dir = tmp_path / "home"
    monkeypatch.setattr(module, "system", lambda: "Linux")

    assert (
        module.resolve_install_path(agent=agent, scope="global", repo_root=None, home_dir=home_dir)
        == home_dir / expected_relative_path
    )


def test_resolve_install_path_global_uses_platform_specific_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home_dir = tmp_path / "home"

    monkeypatch.setattr(module, "system", lambda: "Darwin")
    assert module.resolve_install_path(agent="warp-cli", scope="global", repo_root=None, home_dir=home_dir) == (
        home_dir / "Library" / "Application Support" / "dev.warp.Warp-Stable" / "mcp.json"
    )

    monkeypatch.setattr(module, "system", lambda: "Windows")
    assert module.resolve_install_path(agent="warp-cli", scope="global", repo_root=None, home_dir=home_dir) == (
        home_dir / "AppData" / "Roaming" / "Warp" / "mcp.json"
    )
    assert module.resolve_install_path(agent="crush", scope="global", repo_root=None, home_dir=home_dir) == (
        home_dir / "AppData" / "Local" / "crush" / "crush.json"
    )


@pytest.mark.parametrize(
    ("agent", "scope", "expected_tag", "expected_enabled_flag"),
    [
        ("codex", "global", "codex", None),
        ("copilot", "local", "copilot-workspace", None),
        ("copilot", "global", "copilot-user", None),
        ("claude", "global", "mcp-servers", None),
        ("gemini", "global", "settings", True),
        ("q", "global", "settings", False),
        ("opencode", "global", "opencode", None),
        ("cline", "global", "cline", None),
        ("crush", "global", "crush", None),
    ],
)
def test_install_resolved_mcp_servers_dispatches_to_expected_writer(
    agent: str,
    scope: str,
    expected_tag: str,
    expected_enabled_flag: bool | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved_servers = (_stdio_server("local", True, None, None),)
    install_path = tmp_path / "installed.json"
    record: list[tuple[str, bool | None]] = []

    def fake_resolve_install_path(*, agent: str, scope: str, repo_root: Path | None, home_dir: Path) -> Path:
        return install_path

    def fake_codex(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
        assert path == install_path
        record.append(("codex", None))

    def fake_copilot_workspace(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
        assert path == install_path
        record.append(("copilot-workspace", None))

    def fake_copilot_user(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
        assert path == install_path
        record.append(("copilot-user", None))

    def fake_mcp_servers(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
        assert path == install_path
        record.append(("mcp-servers", None))

    def fake_settings(
        *,
        path: Path,
        resolved_servers: tuple[ResolvedMcpServer, ...],
        ensure_mcp_enabled: bool,
    ) -> None:
        assert path == install_path
        record.append(("settings", ensure_mcp_enabled))

    def fake_opencode(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
        assert path == install_path
        record.append(("opencode", None))

    def fake_cline(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
        assert path == install_path
        record.append(("cline", None))

    def fake_crush(*, path: Path, resolved_servers: tuple[ResolvedMcpServer, ...]) -> None:
        assert path == install_path
        record.append(("crush", None))

    monkeypatch.setattr(module, "resolve_install_path", fake_resolve_install_path)
    monkeypatch.setattr(module, "_write_codex_config", fake_codex)
    monkeypatch.setattr(module, "_write_copilot_workspace_config", fake_copilot_workspace)
    monkeypatch.setattr(module, "_write_copilot_user_config", fake_copilot_user)
    monkeypatch.setattr(module, "_write_mcp_servers_file", fake_mcp_servers)
    monkeypatch.setattr(module, "_write_settings_with_mcp_servers", fake_settings)
    monkeypatch.setattr(module, "_write_opencode_config", fake_opencode)
    monkeypatch.setattr(module, "_write_cline_mcp_settings", fake_cline)
    monkeypatch.setattr(module, "_write_crush_config", fake_crush)

    returned_path = module.install_resolved_mcp_servers(
        agent=agent,
        scope=scope,
        resolved_servers=resolved_servers,
        repo_root=tmp_path,
        home_dir=tmp_path / "home",
    )

    assert returned_path == install_path
    assert record == [(expected_tag, expected_enabled_flag)]


def test_load_json_object_handles_missing_blank_and_comment_json(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"
    blank_path = tmp_path / "blank.json"
    commented_path = tmp_path / "commented.json"

    blank_path.write_text("   ", encoding="utf-8")
    commented_path.write_text('{/*comment*/"value": 1}', encoding="utf-8")

    assert module._load_json_object(path=missing_path) == {}
    assert module._load_json_object(path=blank_path) == {}
    assert module._load_json_object(path=commented_path) == {"value": 1}


def test_ensure_object_member_creates_missing_object_and_rejects_scalar_values(tmp_path: Path) -> None:
    root: dict[str, object] = {}

    created = module._ensure_object_member(root=root, key="mcpServers", path=tmp_path / "settings.json")

    assert created == {}
    assert root["mcpServers"] == {}

    with pytest.raises(ValueError, match="must be a JSON object"):
        module._ensure_object_member(
            root={"mcpServers": 1},
            key="mcpServers",
            path=tmp_path / "settings.json",
        )


def test_write_settings_with_mcp_servers_merges_entries_and_can_enable_mcp(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text('{"keep": true, "mcp": {"enabled": false}}', encoding="utf-8")

    module._write_settings_with_mcp_servers(
        path=path,
        resolved_servers=(_http_server("remote", True, {"Authorization": "Bearer $TOKEN"}, "remote"),),
        ensure_mcp_enabled=True,
    )

    root = _read_json_object(path)
    assert root["keep"] is True
    mcp_settings = cast(dict[str, object], root["mcp"])
    mcp_servers = cast(dict[str, object], root["mcpServers"])
    remote = cast(dict[str, object], mcp_servers["remote"])

    assert mcp_settings["enabled"] is True
    assert remote["url"] == "https://example.com/remote"
    assert remote["headers"] == {"Authorization": "Bearer $TOKEN"}
    assert remote["description"] == "remote"


def test_write_codex_config_replaces_existing_block_and_renders_bearer_token_auth(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """[mcp_servers.alpha]\ncommand = \"old\"\n\n[other]\nvalue = 1\n""",
        encoding="utf-8",
    )

    module._write_codex_config(
        path=path,
        resolved_servers=(
            _http_server("alpha", True, {"Authorization": "Bearer ${API_TOKEN}"}, None),
            _stdio_server("beta", True, None, None),
        ),
    )
    text = path.read_text(encoding="utf-8")

    assert 'command = "old"' not in text
    assert "[mcp_servers.alpha]\nurl = \"https://example.com/alpha\"\nbearer_token_env_var = \"API_TOKEN\"" in text
    assert "[mcp_servers.beta]\ncommand = \"uvx\"\nargs = [\"serve\"]" in text
    assert "[other]\nvalue = 1" in text


def test_cline_writer_marks_disabled_http_servers_and_opencode_rejects_cwd(tmp_path: Path) -> None:
    cline_path = tmp_path / "cline.json"
    module._write_cline_mcp_settings(
        path=cline_path,
        resolved_servers=(_http_server("remote", False, {"Authorization": "Bearer $TOKEN"}, None),),
    )

    root = _read_json_object(cline_path)
    mcp_servers = cast(dict[str, object], root["mcpServers"])
    remote = cast(dict[str, object], mcp_servers["remote"])
    assert remote["type"] == "streamableHttp"
    assert remote["disabled"] is True

    with pytest.raises(ValueError, match="does not support 'cwd'"):
        module._resolved_server_to_opencode_entry(
            resolved_server=_stdio_server("local", True, "/repo", "local server")
        )


@pytest.mark.parametrize(
    ("headers", "message"),
    [
        ({"Authorization": "Token value"}, "Authorization headers of the form"),
        ({"Authorization": "Bearer $TOKEN", "X-Extra": "1"}, "Unsupported headers"),
    ],
)
def test_extract_bearer_token_env_var_rejects_unsupported_headers(
    headers: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        module._extract_bearer_token_env_var(headers=headers, server_name="remote")
