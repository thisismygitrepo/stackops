from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_mcp_impl


@dataclass
class SkillRunCapture:
    install_root: Path | None
    commands: tuple[tuple[str, ...], ...] | None


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
