import json

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.extra_configuration import extended_configuration_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.extensions import collect_extensions
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext


def test_pi_packages_filters_and_autoloaded_extensions(hook_context: DoctorContext) -> None:
    extension_root = hook_context.pi_home / "extensions"
    extension_root.mkdir(parents=True)
    (extension_root / "headroom.ts").write_text("export default function(pi) { pi.on('tool_call', () => {}); }")
    settings = hook_context.pi_home / "settings.json"
    settings.write_text(json.dumps({"packages": ["npm:tk", {"source": "npm:skills-only", "extensions": []}], "extensions": ["./custom.ts"]}))
    inventory = collect_extensions(agent="pi", context=hook_context)
    entries = {entry.name: entry for entry in inventory.entries}
    assert set(entries) == {"npm:tk", "npm:skills-only", "./custom.ts", "headroom"}
    assert entries["npm:skills-only"].state == "disabled"
    assert entries["npm:tk"].removal is not None
    assert entries["npm:tk"].removal.selector == ("packages", 0)
    assert entries["headroom"].removal is not None
    assert entries["headroom"].removal.format == "file"


def test_opencode_jsonc_plugin_registration_and_local_directory(hook_context: DoctorContext) -> None:
    root = hook_context.project_root / ".opencode"
    (root / "plugins").mkdir(parents=True)
    (root / "plugins" / "tk.ts").write_text("export const plugin = async () => ({})")
    (root / "opencode.jsonc").write_text('{// plugins\n"plugin": ["headroom", {"package":"other"}]}')
    inventory = collect_extensions(agent="opencode", context=hook_context)
    assert {entry.name for entry in inventory.entries} == {"headroom", "other", "tk"}
    assert all(entry.origin == "local" for entry in inventory.entries)


def test_omp_yaml_plugin_registry_and_hook_factories(hook_context: DoctorContext) -> None:
    root = hook_context.omp_home
    (root / "hooks" / "pre").mkdir(parents=True)
    (root / "hooks" / "pre" / "tk.ts").write_text("export default function(pi) {}")
    (root / "config.yml").write_text("extensions:\n  - headroom\n")
    registry = root.parent / "plugins"
    registry.mkdir()
    (registry / "omp-plugins.lock.json").write_text(json.dumps({"plugins": {"plugin-hook": {"enabled": True}}}))
    (registry / "package.json").write_text(json.dumps({"dependencies": {"plugin-hook": "*"}}))
    inventory = collect_extensions(agent="omp", context=hook_context)
    entries = {entry.name: entry for entry in inventory.entries}
    assert set(entries) == {"headroom", "plugin-hook", "tk"}
    assert entries["headroom"].removal is not None
    assert entries["headroom"].removal.format == "yaml"
    assert entries["plugin-hook"].removal is not None
    assert entries["plugin-hook"].removal.action == "disable"
    assert entries["tk"].event == "pre (dynamic factory)"


def test_protected_symlink_is_reported_without_scanning(hook_context: DoctorContext) -> None:
    hook_context.pi_home.mkdir(parents=True)
    root = hook_context.pi_home / "extensions"
    root.symlink_to(hook_context.home_directory / "dotfiles" / "extensions")
    inventory = collect_extensions(agent="pi", context=hook_context)
    assert not inventory.entries
    assert any(diagnostic.severity == "error" and "Protected" in diagnostic.message for diagnostic in inventory.diagnostics)


def test_opencode_relative_environment_config_uses_doctor_directory(hook_context: DoctorContext, monkeypatch: pytest.MonkeyPatch) -> None:
    config = hook_context.project_root / "extra.json"
    config.write_text('{"plugin":["headroom"]}')
    monkeypatch.setenv("OPENCODE_CONFIG", "extra.json")
    inventory = collect_extensions(agent="opencode", context=hook_context)
    assert len(inventory.entries) == 1
    assert inventory.entries[0].path == config
    resources = extended_configuration_resources(agent="opencode", context=hook_context)
    assert len(resources) == 1
    assert resources[0].path == config
