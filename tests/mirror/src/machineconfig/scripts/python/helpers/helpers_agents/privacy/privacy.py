from __future__ import annotations

import runpy
import sys
from types import ModuleType

import pytest


MODULE_NAME = "machineconfig.scripts.python.helpers.helpers_agents.privacy.privacy"
EXPECTED_EXPORTS = [
    "apply_max_privacy_and_security_rules_and_configs",
    "secure_mods_config",
    "secure_chatgpt_cli",
    "secure_q_cli",
    "secure_qwen_config",
    "secure_cursor_cli",
    "secure_droid_cli",
    "secure_kilocode_config",
    "secure_cline_config",
    "secure_auggie_config",
    "secure_codex_configs",
]
STUB_IMPORTS: dict[str, str] = {
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.auggie.auggie_privacy": "secure_auggie_config",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt.chatgpt_privacy": "secure_chatgpt_cli",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.cline.cline_privacy": "secure_cline_config",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.codex.codex_privacy": "secure_codex_configs",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.common.privacy_orchestrator": "apply_max_privacy_and_security_rules_and_configs",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.cursor.cursor_privacy": "secure_cursor_cli",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy": "secure_droid_cli",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy": "secure_kilocode_config",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy": "secure_mods_config",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy": "secure_q_cli",
    "machineconfig.scripts.python.helpers.helpers_agents.privacy.configs.qwen.qwen_privacy": "secure_qwen_config",
}


def test_main_exports_expected_names_and_invokes_orchestrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[bool, object | None]] = []

    def _noop() -> None:
        return None

    def _apply(*, overwrite: bool, repo_root: object | None) -> None:
        calls.append((overwrite, repo_root))

    for module_name, attribute_name in STUB_IMPORTS.items():
        module = ModuleType(module_name)
        if attribute_name == "apply_max_privacy_and_security_rules_and_configs":
            setattr(module, attribute_name, _apply)
        else:
            setattr(module, attribute_name, _noop)
        monkeypatch.setitem(sys.modules, module_name, module)

    globals_dict = runpy.run_module(MODULE_NAME, run_name="__main__")

    exported_names = globals_dict["__all__"]
    assert isinstance(exported_names, list)
    assert exported_names == EXPECTED_EXPORTS
    assert calls == [(True, None)]
    for name in EXPECTED_EXPORTS:
        assert callable(globals_dict[name])
