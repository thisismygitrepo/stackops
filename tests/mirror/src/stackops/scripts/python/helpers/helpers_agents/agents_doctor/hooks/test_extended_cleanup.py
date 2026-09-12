import json
import tomllib

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents import codex_config
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan import build_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_resources import collect_cleanup_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.codex_hooks import collect_codex_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookInventory
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext


def test_selective_codex_plugin_cleanup_disables_registration_preserves_cache(hook_context: DoctorContext, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codex_config, "_ADMIN_CONFIG_PATH", hook_context.home_directory / "absent.toml")
    root = hook_context.codex_home / "plugins" / "cache" / "market" / "headroom" / "1"
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"name":"headroom"}')
    config = hook_context.codex_home / "config.toml"
    config.write_text('[plugins."headroom@market"]\nenabled = true\n')

    inventory = collect_cleanup_resources(agent="codex", context=hook_context, resource_focuses=("plugin",))
    plan = build_cleanup_plan(inventory=inventory, scope="global", match="headroom", home_directory=hook_context.home_directory)
    assert not plan.blockers
    apply_cleanup_plan(plan=plan, backup_root=hook_context.home_directory / "backups", home_directory=hook_context.home_directory)
    assert manifest.exists()
    assert tomllib.loads(config.read_text())["plugins"]["headroom@market"]["enabled"] is False


def test_codex_full_reset_removes_profiles_and_cached_inactive_hooks(hook_context: DoctorContext, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codex_config, "_ADMIN_CONFIG_PATH", hook_context.home_directory / "absent.toml")
    root = hook_context.codex_home / "plugins" / "cache" / "market" / "headroom" / "1"
    (root / ".codex-plugin").mkdir(parents=True)
    (root / "hooks").mkdir()
    (root / ".codex-plugin" / "plugin.json").write_text('{"name":"headroom"}')
    (root / "hooks" / "hooks.json").write_text(json.dumps({"hooks": {"Stop": [{"command": "headroom"}]}}))
    config = hook_context.codex_home / "config.toml"
    config.write_text('notify = ["tk"]\n')
    profile = hook_context.codex_home / "custom.config.toml"
    profile.write_text('developer_instructions = "custom instructions"\n')
    instructions = hook_context.project_root / "AGENTS.md"
    instructions.write_text("Custom project instructions")
    hooks = collect_codex_hooks(context=hook_context)
    resources = collect_cleanup_resources(agent="codex", context=hook_context, resource_focuses=("all",))
    inventory = HookInventory((*hooks.entries, *resources.entries), (*hooks.diagnostics, *resources.diagnostics))
    plan = build_cleanup_plan(inventory=inventory, scope="all", match=None, home_directory=hook_context.home_directory)
    assert not plan.blockers
    apply_cleanup_plan(plan=plan, backup_root=hook_context.home_directory / "backups", home_directory=hook_context.home_directory)
    assert not config.exists()
    assert not profile.exists()
    assert not instructions.exists()
    assert not root.exists()


def test_pi_full_reset_preserves_external_package_source(hook_context: DoctorContext) -> None:
    root = hook_context.pi_home
    (root / "extensions").mkdir(parents=True)
    (root / "skills" / "custom").mkdir(parents=True)
    (root / "extensions" / "tk.ts").write_text("export default function(pi) {}")
    (root / "skills" / "custom" / "SKILL.md").write_text("---\nname: custom\n---\nInstructions")
    external = hook_context.home_directory / "source.ts"
    external.write_text("export default function(pi) {}")
    settings = root / "settings.json"
    settings.write_text(json.dumps({"extensions": [str(external)]}))
    inventory = collect_cleanup_resources(agent="pi", context=hook_context, resource_focuses=("all",))
    plan = build_cleanup_plan(inventory=inventory, scope="all", match=None, home_directory=hook_context.home_directory)
    assert not plan.blockers
    apply_cleanup_plan(plan=plan, backup_root=hook_context.home_directory / "backups", home_directory=hook_context.home_directory)
    assert external.exists()
    assert not settings.exists()
    assert not (root / "extensions").exists()
    assert not (root / "skills" / "custom").exists()


@pytest.mark.parametrize("agent", ("codex", "pi", "omp", "opencode"))
def test_instruction_symlink_cleanup_removes_registration_preserves_source(
    hook_context: DoctorContext, monkeypatch: pytest.MonkeyPatch, agent: DoctorAgent
) -> None:
    monkeypatch.setattr(codex_config, "_ADMIN_CONFIG_PATH", hook_context.home_directory / "absent.toml")
    original = hook_context.home_directory / "original-instructions.md"
    original.write_text("Instructions kept by another project")
    registration = hook_context.project_root / "AGENTS.md"
    registration.symlink_to(original)
    inventory = collect_cleanup_resources(agent=agent, context=hook_context, resource_focuses=("instructions",))
    assert any(entry.path == registration for entry in inventory.entries)
    assert all(entry.removal is None or entry.removal.path != original for entry in inventory.entries)
    plan = build_cleanup_plan(inventory=inventory, scope="local", match=None, home_directory=hook_context.home_directory)
    assert not plan.blockers
    result = apply_cleanup_plan(plan=plan, backup_root=hook_context.home_directory / "backups", home_directory=hook_context.home_directory)
    assert result.changed_paths == (registration,)
    assert not registration.is_symlink()
    assert original.read_text() == "Instructions kept by another project"


def test_codex_configuration_symlink_full_reset_preserves_source(hook_context: DoctorContext, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codex_config, "_ADMIN_CONFIG_PATH", hook_context.home_directory / "absent.toml")
    hook_context.codex_home.mkdir()
    original = hook_context.home_directory / "original-config.toml"
    original.write_text('notify = ["tk"]\n')
    registration = hook_context.codex_home / "config.toml"
    registration.symlink_to(original)
    inventory = collect_cleanup_resources(agent="codex", context=hook_context, resource_focuses=("configuration",))
    plan = build_cleanup_plan(inventory=inventory, scope="global", match=None, home_directory=hook_context.home_directory)
    assert not plan.blockers
    result = apply_cleanup_plan(plan=plan, backup_root=hook_context.home_directory / "backups", home_directory=hook_context.home_directory)
    assert result.changed_paths == (registration,)
    assert not registration.is_symlink()
    assert original.read_text() == 'notify = ["tk"]\n'
