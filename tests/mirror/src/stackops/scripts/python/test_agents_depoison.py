import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents, agents_depoison
from stackops.scripts.python.helpers.helpers_agents.agents_doctor import scanning
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgentDefinition, DoctorContext, DoctorExecutableStatus


@pytest.fixture
def isolated_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DoctorContext:
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    context = DoctorContext(
        working_directory=project, project_root=project, ancestor_directories=(project,), home_directory=home,
        xdg_config_directory=home / ".config", xdg_data_directory=home / ".local/share", codex_home=home / ".codex",
        pi_home=home / ".pi/agent", omp_home=home / ".omp/agent", claude_home=home / ".claude",
    )

    def fixture_context(*, working_directory: Path) -> DoctorContext:
        assert working_directory == project
        return context

    def fixture_executable(*, definition: DoctorAgentDefinition) -> DoctorExecutableStatus:
        return DoctorExecutableStatus(installed=False, path=None, version=None, error=definition.agent)

    def execute_worker(command: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert command[:-1] == ["uv", "run", "--no-project", "--python", sys.executable, "--with", "tomlkit", "python", "-c"]
        assert check is False
        try:
            exec(command[-1], {"__name__": "__main__"})
        except SystemExit as error:
            assert isinstance(error.code, int)
            return subprocess.CompletedProcess(args=command, returncode=error.code)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(scanning, "create_doctor_context", fixture_context)
    monkeypatch.setattr(scanning, "_version_status", fixture_executable)
    monkeypatch.setattr(agents_depoison, "subprocess", SimpleNamespace(run=execute_worker))
    return context


def test_full_reset_covers_customizations_and_preserves_unrelated_files(isolated_context: DoctorContext) -> None:
    project = isolated_context.project_root
    settings = project / ".claude/settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "mystery-filter"}]}]}, "model": "custom"}))
    mcp = project / ".mcp.json"
    mcp.write_text(json.dumps({"mcpServers": {"custom-server": {"command": "server"}}}))
    instructions = project / "CLAUDE.md"
    instructions.write_text("Custom instructions")
    skill = project / ".agents/skills/custom/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: custom\n---\nCustom skill")
    plugin = project / ".claude/plugins/example/.claude-plugin/plugin.json"
    plugin.parent.mkdir(parents=True)
    plugin.write_text('{"name":"example"}')
    unrelated = project / "application.py"
    unrelated.write_text("print('keep')")
    auth = isolated_context.claude_home / "credentials.json"
    auth.parent.mkdir(parents=True)
    auth.write_text('{"token":"keep"}')
    runner = CliRunner()
    args = ["depoison", "claude", "--directory", str(project), "--scope", "local"]
    preview = runner.invoke(agents.get_app(), args)
    assert preview.exit_code == 0, preview.output
    for path in (settings, mcp, instructions, skill, plugin):
        assert path.exists()
    assert "configuration" in preview.output
    applied = runner.invoke(agents.get_app(), [*args, "--apply"])
    assert applied.exit_code == 0, applied.output
    for path in (settings, mcp, instructions, skill, plugin):
        assert not path.exists(), path
    assert unrelated.read_text() == "print('keep')"
    assert auth.read_text() == '{"token":"keep"}'
    manifests = tuple(isolated_context.home_directory.glob(".local/state/stackops/depoison/run-*/manifest.json"))
    assert len(manifests) == 1
    assert "settings.json" in manifests[0].read_text()


def test_selected_mcp_removal_preserves_settings_and_other_servers(isolated_context: DoctorContext) -> None:
    project = isolated_context.project_root
    config = project / ".mcp.json"
    config.write_text(json.dumps({"mcpServers": {"headroom": {"command": "proxy"}, "keep": {"command": "server"}}, "other": True}))
    result = CliRunner().invoke(agents.get_app(), [
        "depoison", "claude", "--directory", str(project), "--resource", "mcp", "--match", "headroom", "--apply",
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(config.read_text()) == {"mcpServers": {"keep": {"command": "server"}}, "other": True}


def test_doctor_reports_unknown_local_and_global_hooks(isolated_context: DoctorContext) -> None:
    project = isolated_context.project_root
    for root, command in ((project / ".claude", "unknown-local"), (isolated_context.claude_home, "tk filter")):
        root.mkdir(parents=True)
        (root / "settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]}}))
    result = CliRunner().invoke(agents.get_app(), ["doctor", "claude", "--directory", str(project), "--resource", "hook"])
    assert result.exit_code == 0, result.output
    assert "unknown-local" in result.output
    assert "tk filter" in result.output
    assert "global" in result.output
    assert "local" in result.output
    assert "Hooks" in result.output
    assert "depoison" in result.output


def test_doctor_malformed_hook_config_reports_incomplete_scan(isolated_context: DoctorContext) -> None:
    root = isolated_context.project_root / ".claude"
    root.mkdir()
    (root / "settings.json").write_text("invalid json")
    result = CliRunner().invoke(agents.get_app(), ["doctor", "claude", "--directory", str(isolated_context.project_root)])
    assert result.exit_code == 1, result.output
    assert "incomplete inspection" in result.output


def test_skill_cleanup_unlinks_installed_skill_preserving_source(isolated_context: DoctorContext) -> None:
    project = isolated_context.project_root
    source = isolated_context.home_directory / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("---\nname: linked-skill\n---\nCustom skill")
    link = project / ".agents/skills/linked-skill"
    link.parent.mkdir(parents=True)
    link.symlink_to(source, target_is_directory=True)
    result = CliRunner().invoke(agents.get_app(), [
        "depoison", "claude", "--directory", str(project), "--resource", "skill", "--scope", "local", "--apply",
    ])
    assert result.exit_code == 0, result.output
    assert not link.is_symlink()
    assert (source / "SKILL.md").is_file()


def test_local_mcp_in_user_state_removes_only_selected_project(isolated_context: DoctorContext) -> None:
    project = isolated_context.project_root
    state = isolated_context.home_directory / ".claude.json"
    state.write_text(json.dumps({
        "oauthAccount": {"token": "keep"}, "mcpServers": {"global-server": {"command": "keep"}},
        "projects": {str(project): {"mcpServers": {"local-server": {"command": "remove"}}}, "/other-project": {"mcpServers": {"keep": {"command": "keep"}}}},
    }))
    result = CliRunner().invoke(agents.get_app(), [
        "depoison", "claude", "--directory", str(project), "--resource", "mcp", "--scope", "local", "--apply",
    ])
    assert result.exit_code == 0, result.output
    document = json.loads(state.read_text())
    assert document["projects"][str(project)]["mcpServers"] == {}
    assert document["projects"]["/other-project"]["mcpServers"]["keep"]["command"] == "keep"
    assert document["oauthAccount"]["token"] == "keep"
    assert "global-server" in document["mcpServers"]


def test_worker_preserves_match_with_shell_metacharacters(isolated_context: DoctorContext) -> None:
    project = isolated_context.project_root
    selected_name = """server 'quoted' \"double\" $(printf injected); `printf command` $HOME
second line"""
    config = project / ".mcp.json"
    config.write_text(json.dumps({"mcpServers": {selected_name: {"command": "remove"}, "keep": {"command": "server"}}}))
    result = CliRunner().invoke(agents.get_app(), [
        "depoison", "claude", "--directory", str(project), "--resource", "mcp", "--scope", "local", "--match", selected_name, "--apply",
    ])
    assert result.exit_code == 0, result.output
    assert json.loads(config.read_text()) == {"mcpServers": {"keep": {"command": "server"}}}


def test_worker_reports_invalid_agent(isolated_context: DoctorContext) -> None:
    result = CliRunner().invoke(agents.get_app(), ["depoison", "unknown-agent", "--directory", str(isolated_context.project_root)])
    assert result.exit_code == 2, result.output
    assert "Error:" in result.output
    assert "unknown-agent" in result.output


def test_worker_blocks_partial_cleanup_of_malformed_configuration(isolated_context: DoctorContext) -> None:
    settings = isolated_context.project_root / ".claude/settings.json"
    settings.parent.mkdir()
    settings.write_text("invalid json")
    result = CliRunner().invoke(agents.get_app(), [
        "depoison", "claude", "--directory", str(isolated_context.project_root), "--resource", "hook", "--scope", "local", "--apply",
    ])
    assert result.exit_code == 1, result.output
    assert "Blocked:" in result.output
    assert settings.read_text() == "invalid json"
