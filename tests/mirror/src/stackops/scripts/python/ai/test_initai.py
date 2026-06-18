from pathlib import Path

from stackops.scripts.python.ai.initai import _collect_artifact_changes


def test_collect_artifact_changes_classifies_all_mutations() -> None:
    before = {Path("removed.toml"): (1, 10), Path("written.json"): (1, 20), Path("unchanged.md"): (1, 30)}
    after = {Path("created.toml"): (2, 10), Path("written.json"): (2, 21), Path("unchanged.md"): (1, 30)}

    changes = _collect_artifact_changes(before=before, after=after)

    assert [(change.path.as_posix(), change.action) for change in changes] == [
        ("created.toml", "created"),
        ("removed.toml", "removed"),
        ("written.json", "written"),
    ]
