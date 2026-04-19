

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest


MODULE_NAME = "stackops.scripts.python.helpers.helpers_agents.privacy.privacy"
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
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie.auggie_privacy": "secure_auggie_config",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt.chatgpt_privacy": "secure_chatgpt_cli",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline.cline_privacy": "secure_cline_config",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex.codex_privacy": "secure_codex_configs",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.privacy_orchestrator": "apply_max_privacy_and_security_rules_and_configs",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor.cursor_privacy": "secure_cursor_cli",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy": "secure_droid_cli",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy": "secure_kilocode_config",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy": "secure_mods_config",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy": "secure_q_cli",
    "stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen.qwen_privacy": "secure_qwen_config",
}


def test_main_exports_expected_names_and_invokes_orchestrator(monkeypatch: pytest.MonkeyPatch) -> None:
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

    spec = importlib.util.find_spec(MODULE_NAME)
    assert spec is not None
    assert spec.origin is not None
    module_path = Path(spec.origin)
    globals_dict: dict[str, object] = {"__name__": "__main__", "__file__": str(module_path), "__package__": MODULE_NAME.rpartition(".")[0]}
    exec(module_path.read_text(encoding="utf-8"), globals_dict)

    exported_names = globals_dict["__all__"]
    assert isinstance(exported_names, list)
    assert exported_names == EXPECTED_EXPORTS
    assert calls == [(True, None)]
    for name in EXPECTED_EXPORTS:
        assert callable(globals_dict[name])
