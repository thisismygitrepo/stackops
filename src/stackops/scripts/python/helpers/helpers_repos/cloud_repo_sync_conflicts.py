from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeAlias


if TYPE_CHECKING:
    from git.repo import Repo


type ConflictResolutionAction = Literal["ask", "push-local-merge", "overwrite-local", "stop-on-conflict", "merge-accept-remote", "merge-accept-local"]
ConflictResolutionOption: TypeAlias = Literal[
    "ask", "a", "push-local-merge", "p", "overwrite-local", "o", "stop-on-conflict", "s", "merge-accept-remote", "merge-accept-local"
]
type MergeConflictResolutionSide = Literal["local", "remote"]
type ConflictPathState = Literal["present", "deleted"]


@dataclass(frozen=True)
class MergeConflict:
    path: str
    local: ConflictPathState
    remote: ConflictPathState


def get_merge_conflicts(repo: "Repo") -> tuple[MergeConflict, ...]:
    conflicts: list[MergeConflict] = []
    for path, stage_blobs in sorted(repo.index.unmerged_blobs().items()):
        stages = frozenset(stage for stage, _blob in stage_blobs)
        if 2 not in stages and 3 not in stages:
            raise RuntimeError(f"Unmerged path has neither a local nor remote version: {path}")
        conflicts.append(MergeConflict(path=str(path), local="present" if 2 in stages else "deleted", remote="present" if 3 in stages else "deleted"))
    return tuple(conflicts)


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
        "merge-accept-remote": "merge-accept-remote",
        "merge-accept-local": "merge-accept-local",
    }
    return on_conflict_mapper[on_conflict]


def resolve_merge_conflicts(repo: "Repo", expected_conflicts: tuple[MergeConflict, ...], accept_side: MergeConflictResolutionSide) -> str:
    current_conflicts = get_merge_conflicts(repo=repo)
    if current_conflicts != expected_conflicts:
        raise RuntimeError("Merge conflicts changed after they were presented for resolution.")

    checkout_flag = "--ours" if accept_side == "local" else "--theirs"
    present_paths: list[str] = []
    deleted_paths: list[str] = []
    for conflict in current_conflicts:
        selected_state = conflict.local if accept_side == "local" else conflict.remote
        match selected_state:
            case "present":
                present_paths.append(conflict.path)
            case "deleted":
                deleted_paths.append(conflict.path)

    if len(present_paths) > 0:
        repo.git.checkout(checkout_flag, "--", *present_paths)
        repo.git.add("--", *present_paths)
    if len(deleted_paths) > 0:
        repo.git.rm("--", *deleted_paths)

    unresolved_conflicts = get_merge_conflicts(repo=repo)
    if len(unresolved_conflicts) > 0:
        unresolved_paths = ", ".join(conflict.path for conflict in unresolved_conflicts)
        raise RuntimeError(f"Merge resolution left unresolved paths: {unresolved_paths}")
    repo.git.diff("--cached", "--check")
    repo.git.commit("--no-edit")
    return str(repo.head.commit.hexsha)
