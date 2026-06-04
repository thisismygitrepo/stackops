import stackops
import json
import re
from pathlib import Path
from typing import cast

from stackops.utils.schemas.config.config_types import (
    StackOpsConfig,
    StackOpsConfigStringKey,
)

EXCLUDE_DIRS = [".links", "notebooks",
                "CLAUDE.md", "CRUSH.md", "AGENTS.md",
                ".cursor", ".clinerules", ".github/instructions", ".github/agents", ".github/prompts",
                ".ai",
                ".venv", ".git", ".idea", ".vscode", "node_modules", "__pycache__", ".mypy_cache"
                ]
LIBRARY_ROOT = Path(stackops.__file__).resolve().parent
REPO_ROOT = LIBRARY_ROOT.parent.parent
DOTFILES_ROOT = Path.home().joinpath("dotfiles")
DOTFILES_STACKOPS_ROOT = DOTFILES_ROOT.joinpath("stackops")
DOTFILES_CREDS_ROOT = DOTFILES_ROOT.joinpath("creds")
DOTFILES_SCRIPTS_ROOT = DOTFILES_ROOT.joinpath("scripts")
DOTFILES_STACKOPS_SCRIPTS_ROOT = DOTFILES_STACKOPS_ROOT.joinpath("scripts")
DOTFILES_STACKOPS_SCRIPTS_LINUX_ROOT = DOTFILES_STACKOPS_SCRIPTS_ROOT.joinpath("linux")
DOTFILES_STACKOPS_SCRIPTS_MACOS_ROOT = DOTFILES_STACKOPS_SCRIPTS_ROOT.joinpath("macos")
DOTFILES_STACKOPS_INIT_LINUX_PATH = DOTFILES_STACKOPS_ROOT.joinpath("init_linux.sh")

CONFIG_ROOT = Path.home().joinpath(".config/stackops")
DOTFILES_STACKOPS_CONFIG_PATH = DOTFILES_STACKOPS_ROOT.joinpath("config", "config.json")
DOTFILES_LAYOUTS_JSON_PATH = DOTFILES_STACKOPS_ROOT.joinpath("config", "layouts.json")
DOTFILES_USER_MAPPER_PATH = DOTFILES_STACKOPS_ROOT.joinpath("mapper", "dotfiles.yaml")
DOTFILES_USER_BACKUP_PATH = DOTFILES_STACKOPS_ROOT.joinpath("mapper", "data.yaml")
DOTFILES_MAPPER_FILES_ROOT = DOTFILES_STACKOPS_ROOT.joinpath("mapper", "files")

DOTFILES_PASSWORDS_ROOT = DOTFILES_CREDS_ROOT.joinpath("passwords")
DOTFILES_SSL_ORIGIN_SERVER_ROOT = DOTFILES_PASSWORDS_ROOT.joinpath("ssl", "origin_server")
DOTFILES_SSL_ORIGIN_SERVER_CERT_PATH = DOTFILES_SSL_ORIGIN_SERVER_ROOT.joinpath("cert.pem")
DOTFILES_SSL_ORIGIN_SERVER_KEY_PATH = DOTFILES_SSL_ORIGIN_SERVER_ROOT.joinpath("key.pem")

DOTFILES_RCLONE_CONF_PATH = DOTFILES_CREDS_ROOT.joinpath("rclone", "rclone.conf")
DOTFILES_PYPIRC_PATH = DOTFILES_CREDS_ROOT.joinpath("msc", ".pypirc")
DOTFILES_LLM_CREDS_ROOT = DOTFILES_CREDS_ROOT.joinpath("llm")
DOTFILES_SSH_CREDS_ROOT = DOTFILES_CREDS_ROOT.joinpath(".ssh")
DOTFILES_ZIP_PATH = Path.home().joinpath("dotfiles.zip")

INSTALL_VERSION_ROOT = CONFIG_ROOT.joinpath("cli_tools_installers/versions")
INSTALL_TMP_DIR = Path.home().joinpath("tmp_results", "tmp_installers")

# LINUX_INSTALL_PATH = '/usr/local/bin'
LINUX_INSTALL_PATH = Path.home().joinpath(".local/bin").__str__()
WINDOWS_INSTALL_PATH = Path.home().joinpath("AppData/Local/Microsoft/WindowsApps").__str__()

SCRIPTS_ROOT_PRIVATE = DOTFILES_STACKOPS_SCRIPTS_ROOT  # local directory
SCRIPTS_ROOT_PUBLIC = CONFIG_ROOT.joinpath("scripts")  # local stackops directory
SCRIPTS_ROOT_LIBRARY = LIBRARY_ROOT.joinpath("jobs", "scripts")

SOURCE_OF_TRUTH_PATH_TOKENS: dict[str, Path] = {
    "CONFIG_ROOT": CONFIG_ROOT,
    "DOTFILES_ROOT": DOTFILES_ROOT,
}


def resolve_source_of_truth_path(path_value: str) -> Path:
    for token_name, token_path in SOURCE_OF_TRUTH_PATH_TOKENS.items():
        if path_value == token_name:
            return token_path.expanduser().absolute()
        token_prefix = f"{token_name}/"
        if path_value.startswith(token_prefix):
            return token_path.joinpath(path_value.removeprefix(token_prefix)).expanduser().absolute()
    return Path(path_value).expanduser().absolute()


def _reject_unknown_keys(data: dict[str, object], allowed_keys: set[str], path: str) -> None:
    unknown_keys = sorted(set(data) - allowed_keys)
    if unknown_keys:
        raise ValueError(f"Unexpected StackOps config keys at {path}: {', '.join(unknown_keys)}")


def _require_object(value: object, path: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"StackOps config value at {path} must be an object: {DOTFILES_STACKOPS_CONFIG_PATH}")
    if not all(isinstance(key, str) for key in value):
        raise ValueError(f"StackOps config object at {path} must use string keys: {DOTFILES_STACKOPS_CONFIG_PATH}")
    return cast(dict[str, object], value)


def _require_string(value: object, path: str, *, non_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise ValueError(f"StackOps config value at {path} must be a string: {DOTFILES_STACKOPS_CONFIG_PATH}")
    if non_empty and value == "":
        raise ValueError(f"StackOps config value at {path} must be a non-empty string: {DOTFILES_STACKOPS_CONFIG_PATH}")
    return value


def _require_version(value: object) -> str:
    version = _require_string(value, "version")
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        raise ValueError(f"StackOps config version must use major.minor.patch format: {DOTFILES_STACKOPS_CONFIG_PATH}")
    return version


def read_stackops_config() -> StackOpsConfig:
    if not DOTFILES_STACKOPS_CONFIG_PATH.is_file():
        raise FileNotFoundError(f"StackOps config file not found: {DOTFILES_STACKOPS_CONFIG_PATH}")
    raw_config = _require_object(json.loads(DOTFILES_STACKOPS_CONFIG_PATH.read_text(encoding="utf-8")), "root")
    _reject_unknown_keys(raw_config, {"$schema", "version", "default_rclone_config", "default_email_config", "default_email_address"}, "root")
    config: StackOpsConfig = {
        "version": _require_version(raw_config.get("version")),
    }
    if "$schema" in raw_config:
        config["$schema"] = _require_string(raw_config["$schema"], "$schema", non_empty=False)
    if "default_rclone_config" in raw_config:
        config["default_rclone_config"] = _require_string(raw_config["default_rclone_config"], "default_rclone_config")
    if "default_email_config" in raw_config:
        config["default_email_config"] = _require_string(raw_config["default_email_config"], "default_email_config")
    if "default_email_address" in raw_config:
        config["default_email_address"] = _require_string(raw_config["default_email_address"], "default_email_address")
    return config


def read_stackops_config_string(key: StackOpsConfigStringKey) -> str:
    config = read_stackops_config()
    value = config.get(key)
    if value is None:
        raise KeyError(key)
    return value


def dotfiles_llm_api_keys_path(provider: str) -> Path:
    return DOTFILES_LLM_CREDS_ROOT.joinpath(provider, "api_keys.ini")


# please never look at this file, it contains sensitive data, no matter what.
# even if you are debugging, it doesn't work, whatever, no reason is good enough to justify looking at it.
SECRETS_DOFILE = DOTFILES_STACKOPS_ROOT.joinpath("secrets/secrets.json")
# ---------------


def read_quick_password() -> str:
    from stackops.secrets import search_secrets
    secrets = search_secrets(path=SECRETS_DOFILE, entry_name="quickPassword", keys=("PASSWORD",))
    return secrets[0]["secrets"][0]["keyValues"]["PASSWORD"]


def read_virus_total_api_key() -> str:
    from stackops.secrets import search_secrets

    secrets = search_secrets(path=SECRETS_DOFILE, entry_name="virusTotal", keys=("API_KEY",))
    return secrets[0]["secrets"][0]["keyValues"]["API_KEY"]


def read_email():
    pass


if __name__ == "__main__":
    # print(res)
    pass
