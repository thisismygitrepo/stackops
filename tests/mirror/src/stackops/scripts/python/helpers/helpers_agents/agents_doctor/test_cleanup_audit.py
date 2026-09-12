import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan import build_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resources import collect_cleanup_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import scan_plugin_roots, scan_skill_roots


@pytest.fixture
def audit_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DoctorContext:
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("CLINE_DATA_DIR", raising=False)
    return DoctorContext(
        project,
        project,
        (project,),
        home,
        home / ".config",
        home / ".local/share",
        home / ".codex",
        home / ".pi/agent",
        home / ".omp/agent",
        home / ".claude",
    )


def test_mcp_command_match_identifies_nonmatching_server_name(audit_context: DoctorContext) -> None:
    path = audit_context.project_root / ".mcp.json"
    path.write_text(
        json.dumps({"mcpServers": {"optimizer": {"command": "headroom", "args": ["mcp"]}, "other": {"command": "keep"}}}), encoding="utf-8"
    )
    inventory = collect_cleanup_resources(agent="claude", context=audit_context, resource_focuses=("mcp",))
    plan = build_cleanup_plan(inventory=inventory, scope="local", match="headroom", home_directory=audit_context.home_directory)
    assert len(plan.changes) == 1
    assert plan.changes[0].replacement is not None
    assert json.loads(plan.changes[0].replacement) == {"mcpServers": {"other": {"command": "keep"}}}


def test_linked_skill_cleanup_preserves_external_source(audit_context: DoctorContext) -> None:
    source = audit_context.home_directory / "source-skill"
    source.mkdir()
    (source / "SKILL.md").write_text("Shared content", encoding="utf-8")
    link = audit_context.project_root / ".agents/skills/shared"
    link.parent.mkdir(parents=True)
    link.symlink_to(source, target_is_directory=True)
    inventory = collect_cleanup_resources(agent="claude", context=audit_context, resource_focuses=("skill",))
    plan = build_cleanup_plan(inventory=inventory, scope="local", match="shared", home_directory=audit_context.home_directory)
    assert not plan.blockers
    assert len(plan.changes) == 1
    assert plan.changes[0].snapshot.path == link
    apply_cleanup_plan(plan=plan, backup_root=audit_context.home_directory / "backups", home_directory=audit_context.home_directory)
    assert not link.is_symlink()
    assert (source / "SKILL.md").read_text(encoding="utf-8") == "Shared content"


def test_protected_plugin_root_is_not_statted_as_directory(audit_context: DoctorContext, monkeypatch: pytest.MonkeyPatch) -> None:
    link = audit_context.project_root / "plugins"
    link.symlink_to(audit_context.home_directory / "dotfiles/plugins", target_is_directory=True)
    original_is_dir = Path.is_dir

    def checked_is_dir(path: Path) -> bool:
        assert path != link, "Plugin scanner followed a protected directory link"
        return original_is_dir(path)

    monkeypatch.setattr(Path, "is_dir", checked_is_dir)
    assert scan_plugin_roots(roots=(("local", link, "plugins"),), patterns=("**/*.json",), state="configured") == ()


def test_protected_skill_link_is_reported_without_reading_target(audit_context: DoctorContext, monkeypatch: pytest.MonkeyPatch) -> None:
    root = audit_context.project_root / "skills"
    root.mkdir()
    link = root / "protected"
    link.symlink_to(audit_context.home_directory / "dotfiles/skill", target_is_directory=True)
    original_is_file = Path.is_file

    def checked_is_file(path: Path) -> bool:
        assert not path.is_relative_to(link), "Skill scanner followed a protected skill link"
        return original_is_file(path)

    monkeypatch.setattr(Path, "is_file", checked_is_file)
    resources = scan_skill_roots(roots=(("local", root, "skills"),), recursive=False, state="configured")
    assert len(resources) == 1
    assert resources[0].path == link / "SKILL.md"


def test_cline_full_reset_covers_native_cli_customizations(audit_context: DoctorContext) -> None:
    root = audit_context.project_root / ".cline"
    for suffix, content in (
        ("mcp.json", '{"mcpServers": {}}'),
        ("agents.yaml", "agents: []"),
        ("rules/custom.md", "custom rule"),
        ("skills/custom/SKILL.md", "custom skill"),
        ("plugins/custom.ts", "export default {}"),
    ):
        path = root / suffix
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    global_rule = audit_context.home_directory / ".cline/data/settings/rules/global.md"
    global_rule.parent.mkdir(parents=True)
    global_rule.write_text("global rule", encoding="utf-8")
    inventory = collect_cleanup_resources(agent="cline", context=audit_context, resource_focuses=("all",))
    local_plan = build_cleanup_plan(inventory=inventory, scope="local", match=None, home_directory=audit_context.home_directory)
    assert not local_plan.blockers
    changed = {change.snapshot.path for change in local_plan.changes}
    assert {root / "mcp.json", root / "agents.yaml", root / "rules/custom.md", root / "skills/custom", root / "plugins"}.issubset(changed)
    assert global_rule not in changed
    global_plan = build_cleanup_plan(inventory=inventory, scope="global", match=None, home_directory=audit_context.home_directory)
    assert global_rule in {change.snapshot.path for change in global_plan.changes}


def test_linked_instruction_cleanup_preserves_external_source(audit_context: DoctorContext) -> None:
    source = audit_context.home_directory / "shared-rule.md"
    source.write_text("shared instructions", encoding="utf-8")
    link = audit_context.project_root / ".claude/rules/shared.md"
    link.parent.mkdir(parents=True)
    link.symlink_to(source)
    inventory = collect_cleanup_resources(agent="claude", context=audit_context, resource_focuses=("instructions",))
    plan = build_cleanup_plan(inventory=inventory, scope="local", match="shared", home_directory=audit_context.home_directory)
    assert not plan.blockers
    assert len(plan.changes) == 1
    assert plan.changes[0].snapshot.path == link
    apply_cleanup_plan(plan=plan, backup_root=audit_context.home_directory / "backups", home_directory=audit_context.home_directory)
    assert not link.is_symlink()
    assert source.read_text(encoding="utf-8") == "shared instructions"
