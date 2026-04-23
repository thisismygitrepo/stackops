from collections.abc import Sequence
from dataclasses import dataclass
import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_mcp_impl


@dataclass
class SkillRunCapture:
    install_root: Path | None
    commands: tuple[tuple[str, ...], ...] | None


def make_multi_repo_workspace(tmp_path: Path) -> Path:
    workspace_path = tmp_path / "workspace"
    workspace_path.mkdir()
    for repo_name in ("api", "web"):
        repo_path = workspace_path / repo_name
        repo_path.mkdir()
        repo_path.joinpath(".git").mkdir()
    return workspace_path


def test_add_mcp_routes_caveman_to_agent_skill_installer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reports: list[str] = []
    capture = SkillRunCapture(install_root=None, commands=None)

    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    def fake_run_agent_skill_install_commands(*, install_root: Path, commands: Sequence[tuple[str, ...]]) -> None:
        capture.install_root = install_root
        capture.commands = tuple(commands)

    monkeypatch.setattr(agents_mcp_impl, "get_repo_root", fake_get_repo_root)
    monkeypatch.setattr(agents_mcp_impl, "run_agent_skill_install_commands", fake_run_agent_skill_install_commands)

    agents_mcp_impl.add_mcp(
        requested_mcp_servers="caveman",
        agents="codex",
        scope="local",
        where="library",
        edit=False,
        report=reports.append,
    )

    assert reports == ["Installing agent skills through skills CLI: caveman"]
    assert capture.install_root == tmp_path
    assert capture.commands == (("bunx", "skills", "add", "JuliusBrussee/caveman", "--agent", "codex", "--yes"),)


def test_add_mcp_routes_skill_install_to_multi_repo_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reports: list[str] = []
    capture = SkillRunCapture(install_root=None, commands=None)
    workspace_path = make_multi_repo_workspace(tmp_path)

    def fake_get_repo_root(_path: Path) -> Path | None:
        return None

    def fake_run_agent_skill_install_commands(*, install_root: Path, commands: Sequence[tuple[str, ...]]) -> None:
        capture.install_root = install_root
        capture.commands = tuple(commands)

    monkeypatch.chdir(workspace_path)
    monkeypatch.setattr(agents_mcp_impl, "get_repo_root", fake_get_repo_root)
    monkeypatch.setattr(agents_mcp_impl, "run_agent_skill_install_commands", fake_run_agent_skill_install_commands)

    agents_mcp_impl.add_mcp(
        requested_mcp_servers="caveman",
        agents="codex",
        scope="local",
        where="library",
        edit=False,
        report=reports.append,
    )

    assert reports == ["Installing agent skills through skills CLI: caveman"]
    assert capture.install_root == workspace_path
    assert capture.commands == (("bunx", "skills", "add", "JuliusBrussee/caveman", "--agent", "codex", "--yes"),)


def test_add_mcp_rejects_mixed_mcp_and_skill_names() -> None:
    with pytest.raises(ValueError, match="Do not mix MCP server names and agent skill names"):
        agents_mcp_impl.add_mcp(
            requested_mcp_servers="caveman,tmux",
            agents="codex",
            scope="local",
            where="library",
            edit=False,
            report=lambda _message: None,
        )


def test_add_mcp_installs_postgres_from_library_catalog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reports: list[str] = []

    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr(agents_mcp_impl, "get_repo_root", fake_get_repo_root)

    agents_mcp_impl.add_mcp(
        requested_mcp_servers="postgres",
        agents="codex",
        scope="local",
        where="library",
        edit=False,
        report=reports.append,
    )

    install_path = tmp_path / ".codex" / "config.toml"
    config_text = install_path.read_text(encoding="utf-8")

    assert reports == ["Installing: postgres (library)", f"codex: {install_path}"]
    assert "[mcp_servers.postgres]" in config_text
    assert 'command = "uvx"' in config_text
    assert 'args = ["postgres-mcp", "--access-mode=unrestricted"]' in config_text
    assert "[mcp_servers.postgres.env]" in config_text
    assert 'DATABASE_URI = "postgresql://username:password@localhost:5432/dbname"' in config_text


def test_add_mcp_installs_postgres_from_multi_repo_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reports: list[str] = []
    workspace_path = make_multi_repo_workspace(tmp_path)

    def fake_get_repo_root(_path: Path) -> Path | None:
        return None

    monkeypatch.chdir(workspace_path)
    monkeypatch.setattr(agents_mcp_impl, "get_repo_root", fake_get_repo_root)

    agents_mcp_impl.add_mcp(
        requested_mcp_servers="postgres",
        agents="codex",
        scope="local",
        where="library",
        edit=False,
        report=reports.append,
    )

    install_path = workspace_path / ".codex" / "config.toml"
    config_text = install_path.read_text(encoding="utf-8")

    assert reports == ["Installing: postgres (library)", f"codex: {install_path}"]
    assert "[mcp_servers.postgres]" in config_text


def test_add_mcp_rejects_plain_directory_for_local_scope(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path | None:
        return None

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(agents_mcp_impl, "get_repo_root", fake_get_repo_root)

    with pytest.raises(ValueError, match="workspace directory containing multiple git repositories"):
        agents_mcp_impl.add_mcp(
            requested_mcp_servers="postgres",
            agents="codex",
            scope="local",
            where="library",
            edit=False,
            report=lambda _message: None,
        )


def test_add_mcp_installs_postgres_for_default_agents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_path: Path) -> Path:
        return tmp_path

    monkeypatch.setattr(agents_mcp_impl, "get_repo_root", fake_get_repo_root)

    agents_mcp_impl.add_mcp(
        requested_mcp_servers="postgres",
        agents="",
        scope="local",
        where="library",
        edit=False,
        report=lambda _message: None,
    )

    shared_mcp_config: object = json.loads(tmp_path.joinpath(".mcp.json").read_text(encoding="utf-8"))

    assert isinstance(shared_mcp_config, dict)
    assert "mcpServers" in shared_mcp_config
    assert tmp_path.joinpath(".codex/config.toml").is_file()
