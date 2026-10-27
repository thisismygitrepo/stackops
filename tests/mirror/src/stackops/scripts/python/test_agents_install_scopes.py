from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents import agents_mcp_impl, agents_skill_impl
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import SKILL_INSTALL_BACKEND
from stackops.scripts.python.helpers.helpers_agents.agents_skill_types import SKILL_INSTALL_SCOPE
from stackops.scripts.python.helpers.helpers_agents.mcp_install import MCP_INSTALL_SCOPE
from stackops.scripts.python.helpers.helpers_agents.mcp_types import MCP_CATALOG_SOURCE


@pytest.mark.parametrize(
    ("arguments", "expected_scope"),
    [((), "project"), (("project",), "project"), (("p",), "project"), (("user",), "user"), (("u",), "user")],
)
def test_add_mcp_normalizes_install_scope(
    arguments: tuple[str, ...], expected_scope: MCP_INSTALL_SCOPE, monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_scopes: list[MCP_INSTALL_SCOPE] = []

    def capture_install(
        *,
        requested_mcp_servers: str | None,
        agents: str,
        scope: MCP_INSTALL_SCOPE,
        source: MCP_CATALOG_SOURCE,
        custom_path: Path | None,
        edit: bool,
        report: agents_mcp_impl.Reporter,
    ) -> None:
        assert requested_mcp_servers == "example"
        assert agents == ""
        assert source == "all"
        assert custom_path is None
        assert edit is False
        assert callable(report)
        installed_scopes.append(scope)

    monkeypatch.setattr(agents_mcp_impl, "add_mcp", capture_install)
    scope_arguments = ["--scope", *arguments] if arguments else []

    result = CliRunner().invoke(agents.get_app(), ["add-mcp", "example", *scope_arguments])

    assert result.exit_code == 0, result.output
    assert installed_scopes == [expected_scope]


@pytest.mark.parametrize(
    ("arguments", "expected_scope"),
    [((), "project"), (("project",), "project"), (("p",), "project"), (("user",), "user"), (("u",), "user")],
)
def test_add_skill_normalizes_install_scope(
    arguments: tuple[str, ...], expected_scope: SKILL_INSTALL_SCOPE, monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed_scopes: list[SKILL_INSTALL_SCOPE] = []

    def capture_install(
        *,
        skill_name: str | None,
        group: str | None,
        agent: str | None,
        scope: SKILL_INSTALL_SCOPE,
        directory: str | None,
        reference: bool,
        backend: SKILL_INSTALL_BACKEND,
        yes: bool,
    ) -> int:
        assert skill_name == "orca-cli"
        assert group is None
        assert agent is None
        assert directory is None
        assert reference is False
        assert backend == "stackops"
        assert yes is False
        installed_scopes.append(scope)
        return 0

    monkeypatch.setattr(agents_skill_impl, "add_skill", capture_install)
    scope_arguments = ["--scope", *arguments] if arguments else []

    result = CliRunner().invoke(agents.get_app(), ["add-skill", "orca-cli", *scope_arguments])

    assert result.exit_code == 0, result.output
    assert installed_scopes == [expected_scope]


@pytest.mark.parametrize("command_name", ["add-mcp", "add-skill"])
@pytest.mark.parametrize("removed_scope", ["local", "global"])
def test_install_commands_reject_removed_scope_names(command_name: str, removed_scope: str) -> None:
    result = CliRunner().invoke(agents.get_app(), [command_name, "example", "--scope", removed_scope])

    assert result.exit_code == 2, result.output
