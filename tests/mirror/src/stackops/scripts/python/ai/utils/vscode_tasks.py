import json
from pathlib import Path
from typing import cast

import stackops.scripts.python.ai.scripts.paths as ai_script_paths
import stackops.scripts.python.ai.utils.vscode_tasks as vscode_tasks_module

POSIX_LINT_AND_TYPE_CHECK_PATH = (
    "./" + ai_script_paths.LINT_AND_TYPE_CHECK_REPO_RELATIVE_PATH.as_posix()
)
WINDOWS_LINT_AND_TYPE_CHECK_PATH = ".\\" + ai_script_paths.LINT_AND_TYPE_CHECK_REPO_RELATIVE_PATH.as_posix().replace("/", "\\")


def _read_tasks_config(repo_root: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(repo_root.joinpath(".vscode", "tasks.json").read_text(encoding="utf-8")))


def test_add_lint_and_type_check_task_creates_tasks_file(tmp_path: Path) -> None:
    vscode_tasks_module.add_lint_and_type_check_task(repo_root=tmp_path)

    tasks_config = _read_tasks_config(repo_root=tmp_path)
    tasks = cast(list[dict[str, object]], tasks_config["tasks"])
    lint_task = tasks[0]

    assert tasks_config["version"] == "2.0.0"
    assert len(tasks) == 1
    assert lint_task["label"] == "lint_and_type_check"
    assert lint_task["linux"] == {"command": "uv", "args": ["run", POSIX_LINT_AND_TYPE_CHECK_PATH]}
    assert lint_task["osx"] == {"command": "uv", "args": ["run", POSIX_LINT_AND_TYPE_CHECK_PATH]}
    assert lint_task["windows"] == {"command": "uv", "args": ["run", WINDOWS_LINT_AND_TYPE_CHECK_PATH]}


def test_add_lint_and_type_check_task_replaces_existing_duplicate_label(tmp_path: Path) -> None:
    vscode_dir = tmp_path.joinpath(".vscode")
    vscode_dir.mkdir()
    vscode_dir.joinpath("tasks.json").write_text(
        json.dumps({"version": "2.0.0", "tasks": [{"label": "lint_and_type_check", "type": "shell"}, {"label": "keep-me", "type": "shell"}]}),
        encoding="utf-8",
    )

    vscode_tasks_module.add_lint_and_type_check_task(repo_root=tmp_path)

    tasks = cast(list[dict[str, object]], _read_tasks_config(repo_root=tmp_path)["tasks"])
    labels = [cast(str, task["label"]) for task in tasks]

    assert labels.count("lint_and_type_check") == 1
    assert "keep-me" in labels
