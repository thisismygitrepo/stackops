import platform
import shutil
from collections.abc import Sequence
from pathlib import Path

import machineconfig.scripts.python.ai.scripts.paths as ai_script_paths
from machineconfig.utils.source_of_truth import LIBRARY_ROOT

def create_dot_scripts(repo_root: Path) -> None:
    scripts_dir = LIBRARY_ROOT.joinpath("scripts/python/ai/scripts")
    target_dir = repo_root.joinpath(ai_script_paths.TYPE_CHECKING_SCRIPTS_DIRECTORY)
    shutil.rmtree(target_dir, ignore_errors=True)
    target_dir.mkdir(parents=True, exist_ok=True)

    for script_name in ai_script_paths.TYPE_CHECKING_SCRIPT_PATH_REFERENCES:
        script_path = scripts_dir.joinpath(script_name)
        target_dir.joinpath(script_path.name).write_text(
            data=script_path.read_text(encoding="utf-8"), encoding="utf-8"
        )


def adjust_for_os(config_path: Path) -> str:
    if config_path.suffix not in [".md", ".txt"]:
        return config_path.read_text(encoding="utf-8")
    english_text = config_path.read_text(encoding="utf-8")
    if platform.system() == "Windows":
        return (
            english_text.replace("bash", "PowerShell")
            .replace("sh ", "pwsh ")
            .replace("./", ".\\")
            .replace(".sh", ".ps1")
        )
    elif platform.system() in ["Linux", "Darwin"]:
        return (
            english_text.replace("PowerShell", "bash")
            .replace("pwsh ", "sh ")
            .replace(".\\", "./")
            .replace(".ps1", ".sh")
        )
    else:
        raise NotImplementedError(f"Platform {platform.system()} is not supported.")


def adjust_gitignore(
    repo_root: Path, include_default_entries: bool, extra_entries: Sequence[str]
) -> None:
    dot_git_ignore_path = repo_root.joinpath(".gitignore")
    if dot_git_ignore_path.exists() is False:
        return

    dot_git_ignore_content = dot_git_ignore_path.read_text(encoding="utf-8")
    existing_entries = {
        line.strip()
        for line in dot_git_ignore_content.splitlines()
        if line.strip() != "" and line.lstrip().startswith("#") is False
    }
    desired_entries: list[str] = []
    if include_default_entries:
        from machineconfig.utils.source_of_truth import EXCLUDE_DIRS

        desired_entries.extend(EXCLUDE_DIRS)
    desired_entries.extend(
        entry.strip() for entry in extra_entries if entry.strip() != ""
    )

    entries_to_add: list[str] = []
    for entry in dict.fromkeys(desired_entries):
        if entry not in existing_entries:
            entries_to_add.append(entry)

    if len(entries_to_add) == 0:
        return

    separator = (
        ""
        if dot_git_ignore_content == "" or dot_git_ignore_content.endswith("\n")
        else "\n"
    )
    dot_git_ignore_path.write_text(
        data=dot_git_ignore_content + separator + "\n".join(entries_to_add) + "\n",
        encoding="utf-8",
    )
