from pathlib import Path
from typing import cast


SCRIPT_SUFFIXES: frozenset[str] = frozenset({".py", ".sh", ".ps1", ".bat", ".cmd", ""})
IGNORED_SCRIPT_DIRECTORY_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    ".git",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
})


def is_supported_script_path(relative_path: Path, supported_suffixes: frozenset[str]) -> bool:
    if relative_path.name == "__init__.py" or relative_path.suffix not in SCRIPT_SUFFIXES:
        return False
    if any(part in IGNORED_SCRIPT_DIRECTORY_NAMES for part in relative_path.parts[:-1]):
        return False
    return relative_path.suffix in supported_suffixes


def list_dynamic_script_names() -> list[str]:
    import requests

    api_url = "https://api.github.com/repos/thisismygitrepo/stackops/contents/src/stackops/jobs/scripts_dynamic"
    response = requests.get(api_url, timeout=10)
    response.raise_for_status()
    entries = cast(list[dict[str, str]], response.json())
    return sorted(
        entry["name"]
        for entry in entries
        if entry["type"] == "file" and is_supported_script_path(relative_path=Path(entry["name"]), supported_suffixes=SCRIPT_SUFFIXES)
    )
