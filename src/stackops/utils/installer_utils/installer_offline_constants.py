from pathlib import Path
from typing import Final

from stackops.utils.source_of_truth import CONFIG_ROOT as SOURCE_CONFIG_ROOT
from stackops.utils.source_of_truth import LINUX_INSTALL_PATH, WINDOWS_INSTALL_PATH

CONFIG_ROOT: Path = SOURCE_CONFIG_ROOT
UV_TOOL_BINARIES: list[str] = [
    "devops", "cloud", "agents", "terminal", "fire", "croshell", "utils", "seek", "explore",
]
UV_TOOL_NAME: Final[str] = "stackops"
UV_TOOLS_ROOT: Path = Path.home().joinpath(".local/share/uv/tools")

BINARY_NAMES: list[str] = [
    "bat",
    "cpz",
    "duckdb",
    "gitcs",
    "hyperfine",
    "lazysql",
    "procs",
    "rmz",
    "tv",
    "watchexec",
    "zellij",
    "broot",
    "delta",
    "fastfetch",
    "gitui",
    "jq",
    "lsd",
    "rainfrog",
    "rusty-rain",
    "uv",
    "ya",
    "zoxide",
    "btm",
    "diskonaut",
    "fd",
    "glow",
    "lazydocker",
    "miniserve",
    "rg",
    "starship",
    "uvx",
    "yazi",
    "cpufetch",
    "dua",
    "fzf",
    "hx",
    "lazygit",
    "ouch",
    "rga",
    "tere",
    "viu",
    "yq",
]
DEFAULT_OUTPUT_ROOT: Path = Path.home().joinpath("tmp_results")


def resolve_install_path(*, system_name: str) -> Path:
    if system_name == "Windows":
        return Path(WINDOWS_INSTALL_PATH)
    return Path(LINUX_INSTALL_PATH)


def resolve_binary_source_name(*, binary_name: str, system_name: str) -> str:
    if system_name == "Windows":
        return f"{binary_name}.exe"
    return binary_name
