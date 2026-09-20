from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_agents.agents_shell import quote_for_shell
from stackops.scripts.python.helpers.helpers_agents.constants import DEEPSEEK_PRIVACY_PATCH_PATH
from stackops.utils.accessories import get_repo_root
from stackops.utils.sandbox.containers import container_path


def deepseek_patch_paths(*, directory: Path) -> tuple[Path, ...]:
    repo_root = get_repo_root(directory)
    project_root = repo_root if repo_root is not None else directory
    project_patch = project_root / ".dsh" / "cordis.patch.yml"
    if project_patch.is_file():
        return project_patch, DEEPSEEK_PRIVACY_PATCH_PATH
    return (DEEPSEEK_PRIVACY_PATCH_PATH,)


def build_deepseek_command(
    *, profile: Literal["web", "headless"], patch_paths: tuple[Path, ...], container: bool, is_windows: bool
) -> list[str]:
    command = ["dsh", "--profile", profile]
    for path in patch_paths:
        argument = container_path(path, is_windows=is_windows) if container else str(path)
        command.extend(["--patch", argument])
    return command


def render_deepseek_prompt_command(*, command: list[str], prompt_file: Path, is_windows: bool) -> str:
    command_line = " ".join(quote_for_shell(argument, is_windows=is_windows) for argument in command)
    prompt_argument = quote_for_shell(str(prompt_file), is_windows=is_windows)
    if is_windows:
        return f"""& {command_line} -- -- (Get-Content -Raw -Encoding UTF8 {prompt_argument})"""
    return f"""{command_line} -- -- "$(cat {prompt_argument})"
"""
