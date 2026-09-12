import json

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks import codex_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.codex_hooks import collect_codex_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext


def test_codex_merges_json_inline_notify_and_profiles(hook_context: DoctorContext) -> None:
    global_root = hook_context.codex_home
    local_root = hook_context.project_root / ".codex"
    global_root.mkdir()
    local_root.mkdir()
    (global_root / "config.toml").write_text("""notify = ["tk", "notify"]
[[hooks.PreToolUse]]
matcher = "Bash"
[[hooks.PreToolUse.hooks]]
type = "command"
command = "headroom check"
""")
    (local_root / "hooks.json").write_text(json.dumps({"hooks": {"PostToolUse": [{"hooks": [{"command": "custom-hook"}]}]}}))
    (local_root / "config.toml").write_text('notify = ["ignored-local"]\n')
    (global_root / "testing.config.toml").write_text('notify = ["profile-hook"]\n')

    inventory = collect_codex_hooks(context=hook_context)
    assert len(inventory.entries) == 5
    inline = next(entry for entry in inventory.entries if "headroom" in entry.command)
    assert inline.removal is not None
    assert inline.removal.format == "toml"
    assert inline.removal.selector == ("hooks", "PreToolUse", 0, "hooks", 0)
    local = next(entry for entry in inventory.entries if entry.command == "ignored-local")
    assert local.state == "disabled"
    assert any("trust" in diagnostic.message for diagnostic in inventory.diagnostics)
    assert not any(diagnostic.severity == "error" for diagnostic in inventory.diagnostics)


def test_codex_feature_gate_disables_hooks_but_not_notify(hook_context: DoctorContext) -> None:
    hook_context.codex_home.mkdir()
    (hook_context.codex_home / "config.toml").write_text('notify = ["notify-hook"]\n[features]\nhooks = false\n')
    (hook_context.codex_home / "hooks.json").write_text(json.dumps({"hooks": {"Stop": [{"command": "tk"}]}}))
    inventory = collect_codex_hooks(context=hook_context)
    assert {entry.event: entry.state for entry in inventory.entries} == {"notify": "configured", "Stop": "disabled"}


def test_plugin_hook_manifest_paths_and_inline_disable_registration(hook_context: DoctorContext) -> None:
    root = hook_context.codex_home / "plugins" / "cache" / "market" / "headroom" / "1"
    manifest = root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    (hook_context.codex_home / "config.toml").write_text('[plugins."headroom@market"]\nenabled = true\n')
    manifest.write_text(json.dumps({"hooks": ["./policy.json", {"hooks": {"Stop": [{"command": "inline-tk"}]}}]}))
    (root / "policy.json").write_text(json.dumps({"hooks": {"PreToolUse": [{"command": "headroom"}]}}))
    inventory = collect_codex_hooks(context=hook_context)
    assert len(inventory.entries) == 2
    assert {entry.event for entry in inventory.entries} == {"Stop", "PreToolUse"}
    for entry in inventory.entries:
        assert entry.name.startswith("headroom@market:")
        assert entry.removal is not None
        assert entry.removal.path == hook_context.codex_home / "config.toml"
        assert entry.removal.selector == ("plugins", "headroom@market", "enabled")
        assert entry.removal.action == "disable"


def test_cached_plugin_default_hooks_are_available_not_removable(hook_context: DoctorContext) -> None:
    root = hook_context.codex_home / "plugins" / "cache" / "market" / "unused" / "1"
    (root / ".codex-plugin").mkdir(parents=True)
    (root / "hooks").mkdir()
    (root / ".codex-plugin" / "plugin.json").write_text('{"name":"unused"}')
    (root / "hooks" / "hooks.json").write_text(json.dumps({"hooks": {"Stop": [{"command": "unused-hook"}]}}))
    inventory = collect_codex_hooks(context=hook_context)
    assert len(inventory.entries) == 1
    assert inventory.entries[0].state == "available"
    assert inventory.entries[0].removal is None


def test_invalid_hook_paths_are_diagnosed_without_reading_target(hook_context: DoctorContext) -> None:
    root = hook_context.codex_home / "plugins" / "cache" / "market" / "invalid" / "1"
    (root / ".codex-plugin").mkdir(parents=True)
    (root / ".codex-plugin" / "plugin.json").write_text('{"hooks":"./../../outside.json"}')
    inventory = collect_codex_hooks(context=hook_context)
    assert not inventory.entries
    assert any(diagnostic.severity == "error" and "excluded hook path" in diagnostic.message for diagnostic in inventory.diagnostics)


def test_managed_hook_gate_overrides_user_setting(hook_context: DoctorContext) -> None:
    codex_hooks.CODEX_SYSTEM_ROOT.mkdir()
    (codex_hooks.CODEX_SYSTEM_ROOT / "requirements.toml").write_text('[features]\nhooks = false\n')
    hook_context.codex_home.mkdir()
    (hook_context.codex_home / "config.toml").write_text('[features]\nhooks = true\n')
    (hook_context.codex_home / "hooks.json").write_text(json.dumps({"hooks": {"Stop": [{"command": "tk"}]}}))
    inventory = collect_codex_hooks(context=hook_context)
    assert len(inventory.entries) == 1
    assert inventory.entries[0].state == "disabled"
