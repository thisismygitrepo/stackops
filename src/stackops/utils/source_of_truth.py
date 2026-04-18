"""
Utils
"""

import stackops
from pathlib import Path

EXCLUDE_DIRS = [".links", "notebooks",
                "GEMINI.md", "CLAUDE.md", "CRUSH.md", "AGENTS.md",
                ".cursor", ".clinerules", ".github/instructions", ".github/agents", ".github/prompts",
                ".ai",
                ".venv", ".git", ".idea", ".vscode", "node_modules", "__pycache__", ".mypy_cache"
                ]
LIBRARY_ROOT = Path(stackops.__file__).resolve().parent
REPO_ROOT = LIBRARY_ROOT.parent.parent
DOTFILES_ROOT = Path.home().joinpath("dotfiles")
DOTFILES_MCFG_ROOT = DOTFILES_ROOT.joinpath("stackops")

CONFIG_ROOT = Path.home().joinpath(".config/stackops")
DEFAULTS_PATH = DOTFILES_MCFG_ROOT.joinpath("defaults.ini")

INSTALL_VERSION_ROOT = CONFIG_ROOT.joinpath("cli_tools_installers/versions")
INSTALL_TMP_DIR = Path.home().joinpath("tmp_results", "tmp_installers")

# LINUX_INSTALL_PATH = '/usr/local/bin'
LINUX_INSTALL_PATH = Path.home().joinpath(".local/bin").__str__()
WINDOWS_INSTALL_PATH = Path.home().joinpath("AppData/Local/Microsoft/WindowsApps").__str__()

SCRIPTS_ROOT_PRIVATE = DOTFILES_MCFG_ROOT.joinpath("scripts")  # local directory
SCRIPTS_ROOT_PUBLIC = CONFIG_ROOT.joinpath("scripts")  # local stackops directory
SCRIPTS_ROOT_LIBRARY = LIBRARY_ROOT.joinpath("jobs", "scripts")


if __name__ == "__main__":
    pass
