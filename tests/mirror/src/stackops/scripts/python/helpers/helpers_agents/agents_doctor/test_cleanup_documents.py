import json
import tomllib
from pathlib import Path

import pytest
import yaml

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_documents import edit_cleanup_document
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookRemoval


def test_disabling_toml_plugin_preserves_comments_and_other_configuration() -> None:
    original = b'''# user configuration\nmodel = "chosen"\n[plugins."headroom@tools"]\n# keep this note\nenabled = true\n[mcp_servers.keep]\ncommand = "server"\n'''
    result = edit_cleanup_document(
        original=original,
        removals=(HookRemoval(Path("config.toml"), "toml", ("plugins", "headroom@tools", "enabled"), "disable"),),
    )
    parsed = tomllib.loads(result.decode("utf-8"))
    assert parsed["plugins"]["headroom@tools"]["enabled"] is False
    assert parsed["mcp_servers"]["keep"]["command"] == "server"
    assert b"# user configuration" in result and b"# keep this note" in result


def test_plugin_can_be_explicitly_disabled_when_enabled_key_is_absent() -> None:
    result = edit_cleanup_document(
        original=b'{"plugins":{"headroom":{}},"model":"chosen"}',
        removals=(HookRemoval(Path("config.json"), "json", ("plugins", "headroom", "enabled"), "disable"),),
    )
    assert json.loads(result) == {"plugins": {"headroom": {"enabled": False}}, "model": "chosen"}


def test_yaml_hook_cleanup_preserves_unrelated_values() -> None:
    result = edit_cleanup_document(
        original=b'model: chosen\nhooks:\n  before:\n    - command: tk\n',
        removals=(HookRemoval(Path("config.yaml"), "yaml", ("hooks",), "delete"),),
    )
    assert yaml.safe_load(result) == {"model": "chosen"}


def test_parent_removal_subsumes_nested_and_duplicate_selectors() -> None:
    parent = HookRemoval(Path("config.json"), "json", ("hooks", "before"), "delete")
    result = edit_cleanup_document(
        original=b'{"hooks":{"before":[{"command":"tk"}],"after":[{"command":"keep"}]}}',
        removals=(parent, parent, HookRemoval(Path("config.json"), "json", ("hooks", "before", 0), "delete")),
    )
    assert json.loads(result) == {"hooks": {"after": [{"command": "keep"}]}}


def test_duplicate_json_keys_are_rejected_instead_of_losing_configuration() -> None:
    with pytest.raises(ValueError, match="Duplicate configuration key"):
        edit_cleanup_document(
            original=b'{"model":"a","model":"b","hooks":{}}',
            removals=(HookRemoval(Path("config.json"), "json", ("hooks",), "delete"),),
        )


def test_duplicate_yaml_keys_are_rejected_instead_of_losing_configuration() -> None:
    with pytest.raises(ValueError, match="Duplicate configuration key"):
        edit_cleanup_document(
            original=b'model: a\nmodel: b\nhooks: {}\n',
            removals=(HookRemoval(Path("config.yaml"), "yaml", ("hooks",), "delete"),),
        )
