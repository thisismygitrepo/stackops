from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from stackops.scripts.python.ai.initai_models import ArtifactAction, ArtifactChange


type ArtifactWriteMode = Literal["always", "if_missing"]


def write_text_artifact(
    *,
    repo_root: Path,
    path: Path,
    content: str,
    write_mode: ArtifactWriteMode,
) -> ArtifactChange | None:
    path_existed = path.exists()
    if write_mode == "if_missing" and path_existed:
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data=content, encoding="utf-8")
    action: ArtifactAction = "written" if path_existed else "created"
    return ArtifactChange(path=path.relative_to(repo_root), action=action)


def merge_artifact_changes(*, changes: Iterable[ArtifactChange]) -> tuple[ArtifactChange, ...]:
    changes_by_path: dict[Path, ArtifactChange] = {}
    for change in changes:
        previous = changes_by_path.get(change.path)
        if previous is None:
            changes_by_path[change.path] = change
            continue

        if previous.action == "created":
            if change.action == "removed":
                del changes_by_path[change.path]
            continue
        if previous.action == "written":
            if change.action == "removed":
                changes_by_path[change.path] = change
            continue
        if change.action != "removed":
            changes_by_path[change.path] = ArtifactChange(path=change.path, action="written")

    return tuple(changes_by_path[path] for path in sorted(changes_by_path))
