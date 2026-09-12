import json
from pathlib import Path
from typing import cast

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_apply import apply_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_plan import build_cleanup_plan
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookDiagnostic, HookEntry, HookInventory, HookRemoval


def test_match_removes_arbitrary_hooks_and_preserves_other_configuration(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    original = {
        "model": "chosen",
        "hooks": {"before": [{"command": "custom-cleaner"}, {"command": "keep"}, {"command": "custom-killer"}]},
    }
    path.write_text(json.dumps(original), encoding="utf-8")
    inventory = HookInventory(
        entries=tuple(
            HookEntry("claude", "local", path, command, "before", command, "active", HookRemoval(path, "json", ("hooks", "before", index), "delete"))
            for index, command in enumerate(("custom-cleaner", "keep", "custom-killer"))
        ),
        diagnostics=(),
    )
    plan = build_cleanup_plan(inventory=inventory, scope="local", match="custom-", home_directory=tmp_path)
    assert len(plan.entries) == 2
    assert plan.blockers == ()
    assert json.loads(path.read_text(encoding="utf-8")) == original
    result = apply_cleanup_plan(plan=plan, backup_root=tmp_path / "quarantine", home_directory=tmp_path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"model": "chosen", "hooks": {"before": [{"command": "keep"}]}}
    assert result.backup_directory is not None
    assert json.loads((result.backup_directory / "0000-settings.json").read_text(encoding="utf-8")) == original


def test_whole_configuration_and_directory_reset_subsume_hook_edits(tmp_path: Path) -> None:
    root = tmp_path / "plugins"
    root.mkdir()
    path = root / "hooks.json"
    path.write_text('{"hooks": {"before": [{"command": "tk"}]}}', encoding="utf-8")
    inventory = HookInventory(
        entries=(
            HookEntry("claude", "local", path, "tk", "before", "tk", "active", HookRemoval(path, "json", ("hooks", "before", 0), "delete")),
            HookEntry("claude", "local", path, "configuration", "configuration", "", "active", HookRemoval(path, "file", (), "delete")),
            HookEntry("claude", "local", root, "plugins", "plugin", "", "active", HookRemoval(root, "directory", (), "delete")),
        ),
        diagnostics=(),
    )
    plan = build_cleanup_plan(inventory=inventory, scope="all", match=None, home_directory=tmp_path)
    assert len(plan.changes) == 1
    result = apply_cleanup_plan(plan=plan, backup_root=tmp_path / "quarantine", home_directory=tmp_path)
    assert not root.exists()
    assert result.backup_directory is not None
    assert (result.backup_directory / "0000-plugins" / "hooks.json").exists()


def test_scope_selection_and_managed_resources(tmp_path: Path) -> None:
    local = tmp_path / "local.json"
    global_path = tmp_path / "global.json"
    for path in (local, global_path):
        path.write_text('{"hooks": []}', encoding="utf-8")
    inventory = HookInventory(
        entries=(
            HookEntry("claude", "local", local, "hook", "hook", "", "active", HookRemoval(local, "file", (), "delete")),
            HookEntry("claude", "global", global_path, "hook", "hook", "", "active", HookRemoval(global_path, "file", (), "delete")),
            HookEntry("claude", "admin", tmp_path / "managed.json", "managed", "hook", "", "active", None),
        ),
        diagnostics=(),
    )
    plan = build_cleanup_plan(inventory=inventory, scope="local", match=None, home_directory=tmp_path)
    assert len(plan.changes) == 1
    assert plan.changes[0].snapshot.path == local
    all_plan = build_cleanup_plan(inventory=inventory, scope="all", match=None, home_directory=tmp_path)
    assert len(all_plan.blockers) == 1
    with pytest.raises(ValueError, match="Cleanup blocked"):
        apply_cleanup_plan(plan=all_plan, backup_root=tmp_path / "quarantine", home_directory=tmp_path)
    assert local.exists() and global_path.exists()


def test_diagnostics_block_even_when_name_filter_selects_no_hooks(tmp_path: Path) -> None:
    inventory = HookInventory(
        entries=(),
        diagnostics=(HookDiagnostic("codex", "global", tmp_path / "broken.json", "Malformed JSON", "error"),),
    )
    plan = build_cleanup_plan(inventory=inventory, scope="all", match="tk", home_directory=tmp_path)
    assert plan.blockers
    with pytest.raises(ValueError, match="Cleanup blocked"):
        apply_cleanup_plan(plan=plan, backup_root=tmp_path / "quarantine", home_directory=tmp_path)
    assert not (tmp_path / "quarantine").exists()


def test_malformed_file_blocks_other_selected_changes(tmp_path: Path) -> None:
    valid = tmp_path / "valid.json"
    broken = tmp_path / "broken.json"
    valid.write_text('{"hooks": []}', encoding="utf-8")
    broken.write_text("{broken", encoding="utf-8")
    inventory = HookInventory(
        entries=tuple(
            HookEntry("claude", "local", path, "hook", "hook", "", "active", HookRemoval(path, "json", ("hooks",), "delete"))
            for path in (valid, broken)
        ),
        diagnostics=(),
    )
    plan = build_cleanup_plan(inventory=inventory, scope="all", match=None, home_directory=tmp_path)
    with pytest.raises(ValueError, match="Cleanup blocked"):
        apply_cleanup_plan(plan=plan, backup_root=tmp_path / "quarantine", home_directory=tmp_path)
    assert cast(dict[str, object], json.loads(valid.read_text(encoding="utf-8")))["hooks"] == []


def test_full_reset_quarantines_malformed_configuration_despite_parser_diagnostic(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")
    inventory = HookInventory(
        entries=(HookEntry("claude", "global", path, "configuration", "configuration", "", "active", HookRemoval(path, "file", (), "delete")),),
        diagnostics=(HookDiagnostic("claude", "global", path, "Malformed JSON", "error"),),
    )
    plan = build_cleanup_plan(inventory=inventory, scope="all", match=None, home_directory=tmp_path)
    assert not plan.blockers
    result = apply_cleanup_plan(plan=plan, backup_root=tmp_path / "quarantine", home_directory=tmp_path)
    assert not path.exists()
    assert result.backup_directory is not None
    assert (result.backup_directory / "0000-broken.json").read_text(encoding="utf-8") == "{broken"


def test_full_plugin_reset_subsumes_unregistered_cache_entry(tmp_path: Path) -> None:
    path = tmp_path / "plugins"
    path.mkdir()
    inventory = HookInventory(
        entries=(
            HookEntry("codex", "global", path, "plugins", "plugin", "", "active", HookRemoval(path, "directory", (), "delete")),
            HookEntry("codex", "global", path / "cache" / "hooks.json", "tk", "hook", "tk", "available", None),
        ),
        diagnostics=(),
    )
    plan = build_cleanup_plan(inventory=inventory, scope="all", match=None, home_directory=tmp_path)
    assert not plan.blockers
