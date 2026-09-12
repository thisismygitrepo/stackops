import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.discovery import collect_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.json_inventory import collect_json_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookSource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.paths import permitted_hook_path, read_hook_mapping
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorAgent, DoctorContext


@pytest.fixture
def context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DoctorContext:
    for variable in ("COPILOT_HOME", "CURSOR_CONFIG_DIR", "CLINE_HOOKS_DIR", "QWEN_CODE_SYSTEM_SETTINGS_PATH", "QWEN_CODE_SYSTEM_DEFAULTS_PATH"):
        monkeypatch.delenv(variable, raising=False)
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
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


@pytest.mark.parametrize(
    ("agent", "global_suffix", "local_suffix", "direct"),
    [
        ("claude", ".claude/settings.json", ".claude/settings.local.json", False),
        ("cursor-agent", ".cursor/hooks.json", ".cursor/hooks.json", False),
        ("copilot", ".copilot/hooks/custom.json", ".github/hooks/custom.json", False),
        ("qwen", ".qwen/settings.json", ".qwen/settings.json", False),
        ("droid", ".factory/hooks.json", ".factory/hooks.json", True),
        ("q", ".aws/amazonq/cli-agents/custom.json", ".amazonq/cli-agents/custom.json", False),
    ],
)
def test_local_global_hooks_are_generic(context: DoctorContext, agent: DoctorAgent, global_suffix: str, local_suffix: str, direct: bool) -> None:
    for base, suffix, command in (
        (context.home_directory, global_suffix, "headroom hook"),
        (context.project_root, local_suffix, "unknown-wrapper tk --hook"),
    ):
        path = base / suffix
        path.parent.mkdir(parents=True, exist_ok=True)
        hooks = {"FutureEvent": [{"hooks": [{"type": "command", "command": command}]}]}
        path.write_text(json.dumps(hooks if direct else {"hooks": hooks}), encoding="utf-8")
    inventory = collect_hooks(agent=agent, context=context)
    assert len(inventory.entries) == 2
    assert {entry.origin for entry in inventory.entries} == {"global", "local"}
    assert all(entry.event == "FutureEvent" and entry.removal is not None for entry in inventory.entries)
    assert not [error for error in inventory.diagnostics if error.severity == "error"]


def test_prompt_http_and_platform_commands(context: DoctorContext) -> None:
    path = context.project_root / "hooks.json"
    path.write_text(
        json.dumps(
            {
                "disableAllHooks": True,
                "hooks": {
                    "Start": [
                        {"command": "tk", "bash": "bash audit", "powershell": "audit.ps1"},
                        {"type": "prompt", "prompt": "Check carefully"},
                        {"type": "http", "url": "https://hooks.example/check"},
                    ]
                },
            }
        ),
        encoding="utf-8",
    )
    inventory = collect_json_hooks(source=HookSource("copilot", "local", path, ("hooks",)), context=context, state="configured", removal=None)
    assert len(inventory.entries) == 3
    assert all(entry.state == "disabled" for entry in inventory.entries)
    assert "powershell: audit.ps1" in inventory.entries[0].command
    assert "Check carefully" in inventory.entries[1].command
    assert "https://hooks.example/check" in inventory.entries[2].command
    assert inventory.entries[1].removal is not None
    assert inventory.entries[1].removal.selector == ("hooks", "Start", 1)


def test_malformed_sibling_reports_error_and_valid_hook(context: DoctorContext) -> None:
    path = context.project_root / "hooks.json"
    path.write_text(json.dumps({"hooks": {"Start": ["invalid", {"command": "audit"}], "Stop": {"command": "invalid"}}}), encoding="utf-8")
    inventory = collect_json_hooks(source=HookSource("claude", "local", path, ("hooks",)), context=context, state="configured", removal=None)
    assert len(inventory.entries) == 1
    assert len(inventory.diagnostics) == 2
    assert all(error.severity == "error" for error in inventory.diagnostics)
    path.write_text("{broken", encoding="utf-8")
    broken = collect_json_hooks(source=HookSource("claude", "local", path, ("hooks",)), context=context, state="configured", removal=None)
    assert not broken.entries
    assert broken.diagnostics[0].severity == "error"


def test_claude_plugin_hook_disables_registration(context: DoctorContext) -> None:
    plugin = context.claude_home / "plugins/cache/market/headroom/v1"
    (plugin / "hooks").mkdir(parents=True)
    (plugin / "hooks/hooks.json").write_text(
        json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"command": "headroom intercept"}]}]}}), encoding="utf-8"
    )
    settings = context.claude_home / "settings.json"
    settings.write_text(json.dumps({"enabledPlugins": {"headroom@market": True}}), encoding="utf-8")
    (context.claude_home / "plugins/installed_plugins.json").write_text(
        json.dumps({"version": 2, "plugins": {"headroom@market": [{"scope": "user", "installPath": str(plugin)}]}}), encoding="utf-8"
    )
    inventory = collect_hooks(agent="claude", context=context)
    assert len(inventory.entries) == 1
    entry = inventory.entries[0]
    assert entry.name.startswith("headroom@market")
    assert entry.removal is not None
    assert entry.removal.path == settings
    assert entry.removal.selector == ("enabledPlugins", "headroom@market")
    assert entry.removal.action == "disable"


def test_droid_settings_hook_is_shadowed(context: DoctorContext) -> None:
    directory = context.home_directory / ".factory"
    directory.mkdir()
    (directory / "hooks.json").write_text(json.dumps({"Stop": [{"hooks": [{"command": "new"}]}]}), encoding="utf-8")
    (directory / "settings.json").write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"command": "old"}]}]}}), encoding="utf-8")
    inventory = collect_hooks(agent="droid", context=context)
    assert {entry.command: entry.state for entry in inventory.entries} == {"command: new": "configured", "command: old": "shadowed"}


def test_cline_global_and_local_executable_scripts(context: DoctorContext) -> None:
    for base, suffix in ((context.home_directory, "Documents/Cline/Hooks/PreToolUse"), (context.project_root, ".cline/hooks/TaskStart")):
        path = base / suffix
        path.parent.mkdir(parents=True)
        path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        path.chmod(0o755)
    inventory = collect_hooks(agent="cline", context=context)
    assert {entry.origin for entry in inventory.entries} == {"global", "local"}
    assert all(entry.removal is not None and entry.removal.format == "file" for entry in inventory.entries)


def test_protected_symlink_is_rejected_before_read(context: DoctorContext) -> None:
    target = context.home_directory / "dotfiles/private/hooks.json"
    link = context.project_root / "hooks.json"
    link.symlink_to(target)
    assert not permitted_hook_path(path=link, context=context)
    result = read_hook_mapping(path=link, context=context)
    assert isinstance(result, str)
    assert "Protected" in result


def test_managed_hooks_are_visible_and_not_removable(context: DoctorContext) -> None:
    path = context.project_root / "managed-settings.json"
    path.write_text(json.dumps({"hooks": {"Start": [{"command": "managed audit"}]}}), encoding="utf-8")
    inventory = collect_json_hooks(source=HookSource("claude", "admin", path, ("hooks",)), context=context, state="configured", removal=None)
    assert len(inventory.entries) == 1
    assert inventory.entries[0].removal is None


def test_protected_symlink_with_parent_segments_is_rejected(context: DoctorContext) -> None:
    link = context.project_root / "linked"
    link.symlink_to(context.home_directory / "dotfiles/private")
    assert not permitted_hook_path(path=link / ".." / "hooks.json", context=context)


def test_strict_json_settings_report_comments_as_invalid(context: DoctorContext) -> None:
    path = context.project_root / "settings.json"
    path.write_text('{"hooks": {}, // invalid Claude settings\n"model": "x"}', encoding="utf-8")
    result = read_hook_mapping(path=path, context=context)
    assert isinstance(result, str)
    assert "Expecting" in result
