from pathlib import Path

import stackops.scripts.python.helpers.helpers_agents.privacy.configs.aichat as aichat_assets
import stackops.scripts.python.helpers.helpers_agents.privacy.configs.copilot as copilot_assets
import stackops.scripts.python.helpers.helpers_agents.privacy.configs.crush as crush_assets
import stackops.scripts.python.helpers.helpers_agents.privacy.configs.gemini as gemini_assets
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.auggie.auggie_privacy import secure_auggie_config
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.chatgpt.chatgpt_privacy import secure_chatgpt_cli
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.cline.cline_privacy import secure_cline_config
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.codex.codex_privacy import secure_codex_configs
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.cursor.cursor_privacy import secure_cursor_cli
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.droid.droid_privacy import secure_droid_cli
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.kilocode.kilocode_privacy import secure_kilocode_config
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.mods.mods_privacy import secure_mods_config
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.q.q_privacy import secure_q_cli
from stackops.scripts.python.helpers.helpers_agents.privacy.configs.qwen.qwen_privacy import secure_qwen_config
from stackops.utils.path_reference import get_path_reference_path


def apply_max_privacy_and_security_rules_and_configs(overwrite: bool, repo_root: str | None) -> None:
    root = Path(__file__).resolve().parent.parent
    gemini_settings_source = get_path_reference_path(
        module=gemini_assets,
        path_reference=gemini_assets.SETTINGS_PATH_REFERENCE,
    )
    gemini_settings_target_global = Path.home().joinpath(".gemini/settings.json")
    if not gemini_settings_target_global.exists() or overwrite:
        gemini_settings_target_global.parent.mkdir(parents=True, exist_ok=True)
        if gemini_settings_source.exists():
            gemini_settings_target_global.write_text(gemini_settings_source.read_text())
    if repo_root:
        gemini_settings_target_repo = Path(repo_root).joinpath(".gemini/settings.json")
        if not gemini_settings_target_repo.exists() or overwrite:
            gemini_settings_target_repo.parent.mkdir(parents=True, exist_ok=True)
            if gemini_settings_source.exists():
                gemini_settings_target_repo.write_text(gemini_settings_source.read_text())

    aider_settings_source = root.joinpath("aider/.aider.conf.yml")
    aider_settings_target_global = Path.home().joinpath(".aider.conf.yml")
    if not aider_settings_target_global.exists() or overwrite:
        aider_settings_target_global.parent.mkdir(parents=True, exist_ok=True)
        if aider_settings_source.exists():
            aider_settings_target_global.write_text(aider_settings_source.read_text())
    if repo_root:
        aider_settings_target_repo = Path(repo_root).joinpath(".aider.conf.yml")
        if not aider_settings_target_repo.exists() or overwrite:
            aider_settings_target_repo.parent.mkdir(parents=True, exist_ok=True)
            if aider_settings_source.exists():
                aider_settings_target_repo.write_text(aider_settings_source.read_text())

    aichat_settings_source = get_path_reference_path(
        module=aichat_assets,
        path_reference=aichat_assets.CONFIG_PATH_REFERENCE,
    )
    aichat_settings_target_global = Path.home().joinpath(".config/aichat/config.yaml")
    if not aichat_settings_target_global.exists() or overwrite:
        aichat_settings_target_global.parent.mkdir(parents=True, exist_ok=True)
        if aichat_settings_source.exists():
            aichat_settings_target_global.write_text(aichat_settings_source.read_text())
    if repo_root:
        aichat_settings_target_repo = Path(repo_root).joinpath(".config/aichat/config.yaml")
        if not aichat_settings_target_repo.exists() or overwrite:
            aichat_settings_target_repo.parent.mkdir(parents=True, exist_ok=True)
            if aichat_settings_source.exists():
                aichat_settings_target_repo.write_text(aichat_settings_source.read_text())

    copilot_settings_source = get_path_reference_path(
        module=copilot_assets,
        path_reference=copilot_assets.CONFIG_PATH_REFERENCE,
    )
    copilot_settings_target_global = Path.home().joinpath(".config/gh-copilot/config.yml")
    if not copilot_settings_target_global.exists() or overwrite:
        copilot_settings_target_global.parent.mkdir(parents=True, exist_ok=True)
        if copilot_settings_source.exists():
            copilot_settings_target_global.write_text(copilot_settings_source.read_text())
    if repo_root:
        copilot_settings_target_repo = Path(repo_root).joinpath(".config/gh-copilot/config.yml")
        if not copilot_settings_target_repo.exists() or overwrite:
            copilot_settings_target_repo.parent.mkdir(parents=True, exist_ok=True)
            if copilot_settings_source.exists():
                copilot_settings_target_repo.write_text(copilot_settings_source.read_text())

    crush_settings_source = get_path_reference_path(
        module=crush_assets,
        path_reference=crush_assets.CRUSH_PATH_REFERENCE,
    )
    crush_settings_target_global = Path.home().joinpath(".config/crush/crush.json")
    if not crush_settings_target_global.exists() or overwrite:
        crush_settings_target_global.parent.mkdir(parents=True, exist_ok=True)
        if crush_settings_source.exists():
            crush_settings_target_global.write_text(crush_settings_source.read_text())
    if repo_root:
        crush_settings_target_repo = Path(repo_root).joinpath(".crush.json")
        if not crush_settings_target_repo.exists() or overwrite:
            crush_settings_target_repo.parent.mkdir(parents=True, exist_ok=True)
            if crush_settings_source.exists():
                crush_settings_target_repo.write_text(crush_settings_source.read_text())

    try:
        secure_mods_config()
    except Exception:
        pass
    try:
        secure_chatgpt_cli()
    except Exception:
        pass
    try:
        secure_q_cli()
    except Exception:
        pass
    try:
        secure_qwen_config()
    except Exception:
        pass
    try:
        secure_cursor_cli()
    except Exception:
        pass
    try:
        secure_droid_cli()
    except Exception:
        pass
    try:
        secure_kilocode_config()
    except Exception:
        pass
    try:
        secure_cline_config()
    except Exception:
        pass
    try:
        secure_auggie_config()
    except Exception:
        pass
    try:
        secure_codex_configs()
    except Exception:
        pass
