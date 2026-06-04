"""
Utils
"""

import stackops
from pathlib import Path

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
DEFAULTS_PATH = DOTFILES_STACKOPS_ROOT.joinpath("defaults.ini")
DOTFILES_PHONE_NOTIFICATION_INI_PATH = DOTFILES_STACKOPS_ROOT.joinpath("phone_notification.ini")
DOTFILES_LAYOUTS_JSON_PATH = DOTFILES_STACKOPS_ROOT.joinpath("layouts.json")
DOTFILES_WIFI_INI_PATH = DOTFILES_STACKOPS_ROOT.joinpath("setup", "wifi.ini")
DOTFILES_USER_MAPPER_PATH = DOTFILES_STACKOPS_ROOT.joinpath("mapper", "dotfiles.yaml")
DOTFILES_USER_BACKUP_PATH = DOTFILES_STACKOPS_ROOT.joinpath("mapper", "data.yaml")
DOTFILES_MAPPER_FILES_ROOT = DOTFILES_STACKOPS_ROOT.joinpath("mapper", "files")

DOTFILES_PASSWORDS_ROOT = DOTFILES_CREDS_ROOT.joinpath("passwords")
DOTFILES_SSL_ORIGIN_SERVER_ROOT = DOTFILES_PASSWORDS_ROOT.joinpath("ssl", "origin_server")
DOTFILES_SSL_ORIGIN_SERVER_CERT_PATH = DOTFILES_SSL_ORIGIN_SERVER_ROOT.joinpath("cert.pem")
DOTFILES_SSL_ORIGIN_SERVER_KEY_PATH = DOTFILES_SSL_ORIGIN_SERVER_ROOT.joinpath("key.pem")

DOTFILES_TOKENS_ROOT = DOTFILES_CREDS_ROOT.joinpath("tokens")
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
