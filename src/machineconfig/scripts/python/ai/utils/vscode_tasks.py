import json
from pathlib import Path
from typing import cast

import machineconfig.scripts.python.ai.scripts.paths as ai_script_paths

POSIX_LINT_AND_TYPE_CHECK_PATH = (
    "./" + ai_script_paths.LINT_AND_TYPE_CHECK_REPO_RELATIVE_PATH.as_posix()
)
WINDOWS_LINT_AND_TYPE_CHECK_PATH = ".\\" + ai_script_paths.LINT_AND_TYPE_CHECK_REPO_RELATIVE_PATH.as_posix().replace("/", "\\")


def add_lint_and_type_check_task(repo_root: Path) -> None:
    vscode_dir = repo_root / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    tasks_json_path = vscode_dir / "tasks.json"

    task_to_add: dict[str, object] = {
        "label": "lint_and_type_check",
        "type": "shell",
        "linux": {"command": "uv", "args": ["run", POSIX_LINT_AND_TYPE_CHECK_PATH]},
        "osx": {"command": "uv", "args": ["run", POSIX_LINT_AND_TYPE_CHECK_PATH]},
        "windows": {"command": "uv", "args": ["run", WINDOWS_LINT_AND_TYPE_CHECK_PATH]},
        "presentation": {"reveal": "always", "panel": "new"},
        "problemMatcher": [],
    }

    if tasks_json_path.exists():
        json_data = tasks_json_path.read_text(encoding="utf-8")
        if not json_data.strip():
            tasks_config: dict[str, object] = {"version": "2.0.0", "tasks": []}
        else:
            tasks_config = cast(dict[str, object], json.loads(json_data))
        if "tasks" not in tasks_config:
            tasks_config["tasks"] = []

        # Remove any existing entries with the same label to prevent duplicates
        tasks = cast(list[dict[str, object]], tasks_config["tasks"])
        tasks_config["tasks"] = [
            task for task in tasks if task.get("label") != task_to_add["label"]
        ]
        tasks_config["tasks"].append(task_to_add)
    else:
        tasks_config = {"version": "2.0.0", "tasks": [task_to_add]}

    tasks_json_path.write_text(json.dumps(tasks_config, indent="\t"), encoding="utf-8")
