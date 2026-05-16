from pathlib import Path
import shlex
from typing import Literal


ConflictResolutionAction = Literal[
    "ask",
    "push-local-merge",
    "overwrite-local",
    "stop-on-conflict",
    "remove-rclone-conflict",
    "merge-accept-remote",
    "merge-accept-local",
]
ConflictResolutionOption = Literal[
    "ask",
    "a",
    "push-local-merge",
    "p",
    "overwrite-local",
    "o",
    "stop-on-conflict",
    "s",
    "remove-rclone-conflict",
    "r",
    "merge-accept-remote",
    "merge-accept-local",
]
MergeConflictResolutionSide = Literal["local", "remote"]


def _bash_quote(value: str) -> str:
    return shlex.quote(value)


def powershell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _build_conflict_path_arguments(conflict_paths: tuple[str, ...], shell: Literal["bash", "powershell"]) -> str:
    if len(conflict_paths) == 0:
        raise ValueError("Cannot build a conflict-resolution program without conflicted paths.")
    if shell == "bash":
        return " ".join(_bash_quote(path) for path in conflict_paths)
    return " ".join(powershell_single_quote(path) for path in conflict_paths)


def resolve_conflict_action(on_conflict: ConflictResolutionOption) -> ConflictResolutionAction:
    on_conflict_mapper: dict[ConflictResolutionOption, ConflictResolutionAction] = {
        "a": "ask",
        "ask": "ask",
        "p": "push-local-merge",
        "push-local-merge": "push-local-merge",
        "o": "overwrite-local",
        "overwrite-local": "overwrite-local",
        "s": "stop-on-conflict",
        "stop-on-conflict": "stop-on-conflict",
        "r": "remove-rclone-conflict",
        "remove-rclone-conflict": "remove-rclone-conflict",
        "merge-accept-remote": "merge-accept-remote",
        "merge-accept-local": "merge-accept-local",
    }
    return on_conflict_mapper[on_conflict]


def build_merge_accept_program(
    repo_local_root: Path,
    conflict_paths: tuple[str, ...],
    accept_side: MergeConflictResolutionSide,
    push_local_program: str,
    platform_name: str,
) -> str:
    checkout_flag = "--ours" if accept_side == "local" else "--theirs"
    shell_kind: Literal["bash", "powershell"] = "powershell" if platform_name == "Windows" else "bash"
    conflict_args = _build_conflict_path_arguments(conflict_paths=conflict_paths, shell=shell_kind)
    if platform_name == "Windows":
        repo_local_root_quoted = powershell_single_quote(str(repo_local_root))
        return f"""
Set-Location -LiteralPath {repo_local_root_quoted}
git checkout {checkout_flag} -- {conflict_args}
git add -- {conflict_args}
git commit --no-edit
{push_local_program}
"""
    return f"""
cd {_bash_quote(str(repo_local_root))}
git checkout {checkout_flag} -- {conflict_args}
git add -- {conflict_args}
git commit --no-edit
{push_local_program}
"""
