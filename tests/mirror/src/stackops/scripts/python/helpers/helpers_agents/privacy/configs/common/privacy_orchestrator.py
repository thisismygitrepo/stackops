

from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_agents.privacy.configs.aichat as aichat_assets
import stackops.scripts.python.helpers.helpers_agents.privacy.configs.copilot as copilot_assets
import stackops.scripts.python.helpers.helpers_agents.privacy.configs.crush as crush_assets
import stackops.scripts.python.helpers.helpers_agents.privacy.configs.gemini as gemini_assets
import stackops.scripts.python.helpers.helpers_agents.privacy.configs.common.privacy_orchestrator as orchestrator
from stackops.utils.path_reference import get_path_reference_path


HELPER_NAMES = (
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
)


def _patch_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    monkeypatch.setattr(orchestrator.Path, "home", lambda: home)


def _asset_targets(home: Path, repo_root: Path) -> tuple[tuple[Path, Path, Path], ...]:
    root = Path(orchestrator.__file__).resolve().parent.parent
    return (
        (
            get_path_reference_path(module=gemini_assets, path_reference=gemini_assets.SETTINGS_PATH_REFERENCE),
            home / ".gemini" / "settings.json",
            repo_root / ".gemini" / "settings.json",
        ),
        (root / "aider" / ".aider.conf.yml", home / ".aider.conf.yml", repo_root / ".aider.conf.yml"),
        (
            get_path_reference_path(module=aichat_assets, path_reference=aichat_assets.CONFIG_PATH_REFERENCE),
            home / ".config" / "aichat" / "config.yaml",
            repo_root / ".config" / "aichat" / "config.yaml",
        ),
        (
            get_path_reference_path(module=copilot_assets, path_reference=copilot_assets.CONFIG_PATH_REFERENCE),
            home / ".config" / "gh-copilot" / "config.yml",
            repo_root / ".config" / "gh-copilot" / "config.yml",
        ),
        (
            get_path_reference_path(module=crush_assets, path_reference=crush_assets.CRUSH_PATH_REFERENCE),
            home / ".config" / "crush" / "crush.json",
            repo_root / ".crush.json",
        ),
    )


def _patch_secure_helpers(monkeypatch: pytest.MonkeyPatch, failing_helpers: frozenset[str]) -> list[str]:
    calls: list[str] = []

    for helper_name in HELPER_NAMES:

        def _make_helper(name: str) -> object:
            def _helper() -> None:
                calls.append(name)
                if name in failing_helpers:
                    raise RuntimeError(name)

            return _helper

        monkeypatch.setattr(orchestrator, helper_name, _make_helper(helper_name))

    return calls


def test_apply_max_privacy_copies_packaged_assets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)

    _patch_home(monkeypatch=monkeypatch, home=home)
    helper_calls = _patch_secure_helpers(monkeypatch=monkeypatch, failing_helpers=frozenset())

    orchestrator.apply_max_privacy_and_security_rules_and_configs(overwrite=False, repo_root=str(repo_root))

    for source_path, global_target, repo_target in _asset_targets(home=home, repo_root=repo_root):
        source_text = source_path.read_text(encoding="utf-8")
        assert global_target.read_text(encoding="utf-8") == source_text
        assert repo_target.read_text(encoding="utf-8") == source_text

    assert helper_calls == list(HELPER_NAMES)


def test_apply_max_privacy_preserves_existing_targets_when_overwrite_disabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)

    _patch_home(monkeypatch=monkeypatch, home=home)
    _patch_secure_helpers(monkeypatch=monkeypatch, failing_helpers=frozenset())

    for _, global_target, repo_target in _asset_targets(home=home, repo_root=repo_root):
        global_target.parent.mkdir(parents=True, exist_ok=True)
        global_target.write_text("""keep-global""", encoding="utf-8")
        repo_target.parent.mkdir(parents=True, exist_ok=True)
        repo_target.write_text("""keep-repo""", encoding="utf-8")

    orchestrator.apply_max_privacy_and_security_rules_and_configs(overwrite=False, repo_root=str(repo_root))

    for _, global_target, repo_target in _asset_targets(home=home, repo_root=repo_root):
        assert global_target.read_text(encoding="utf-8") == "keep-global"
        assert repo_target.read_text(encoding="utf-8") == "keep-repo"


def test_apply_max_privacy_overwrites_existing_targets_and_continues_after_helper_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)

    _patch_home(monkeypatch=monkeypatch, home=home)
    helper_calls = _patch_secure_helpers(monkeypatch=monkeypatch, failing_helpers=frozenset({"secure_cursor_cli", "secure_cline_config"}))

    gemini_source, global_target, repo_target = _asset_targets(home=home, repo_root=repo_root)[0]
    global_target.parent.mkdir(parents=True, exist_ok=True)
    global_target.write_text("""old-global""", encoding="utf-8")
    repo_target.parent.mkdir(parents=True, exist_ok=True)
    repo_target.write_text("""old-repo""", encoding="utf-8")

    orchestrator.apply_max_privacy_and_security_rules_and_configs(overwrite=True, repo_root=str(repo_root))

    source_text = gemini_source.read_text(encoding="utf-8")
    assert global_target.read_text(encoding="utf-8") == source_text
    assert repo_target.read_text(encoding="utf-8") == source_text
    assert helper_calls == list(HELPER_NAMES)
