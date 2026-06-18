from collections.abc import Sequence
from os import walk
from pathlib import Path
from time import perf_counter
from typing import Final, get_args

import stackops.scripts.python.ai.scripts.paths as ai_script_paths
from stackops.scripts.python.ai.initai_frameworks import build_framework_config
from stackops.scripts.python.ai.initai_models import ArtifactChange, FileState, InitConfigPlan, InitConfigResult
from stackops.scripts.python.ai.initai_rich_output import create_phase_status, show_init_config_plan, show_init_config_result, show_phase_complete
from stackops.scripts.python.ai.utils import generic
from stackops.scripts.python.ai.utils.vscode_tasks import add_lint_and_type_check_task
from stackops.utils.accessories import get_repo_root
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS

_SNAPSHOT_EXCLUDED_DIRECTORY_NAMES: Final[frozenset[str]] = frozenset(
    {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".venv", "__pycache__", "node_modules"}
)


def _snapshot_repo_files(repo_root: Path) -> dict[Path, FileState]:
    files_state: dict[Path, FileState] = {}
    for current_root, directory_names, file_names in walk(repo_root):
        directory_names[:] = [directory_name for directory_name in directory_names if directory_name not in _SNAPSHOT_EXCLUDED_DIRECTORY_NAMES]
        current_root_path = Path(current_root)
        for file_name in file_names:
            path = current_root_path / file_name
            file_stat = path.lstat()
            files_state[path.relative_to(repo_root)] = (file_stat.st_mtime_ns, file_stat.st_size)
    return files_state


def _collect_artifact_changes(*, before: dict[Path, FileState], after: dict[Path, FileState]) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    for path in sorted(before.keys() | after.keys()):
        before_state = before.get(path)
        after_state = after.get(path)
        if before_state is None:
            changes.append(ArtifactChange(path=path, action="created"))
        elif after_state is None:
            changes.append(ArtifactChange(path=path, action="removed"))
        elif before_state != after_state:
            changes.append(ArtifactChange(path=path, action="written"))
    return tuple(changes)


def _collect_gitignore_entries(*, changes: tuple[ArtifactChange, ...]) -> tuple[str, ...]:
    return tuple(change.path.as_posix() for change in changes if change.action != "removed" and change.path != Path(".gitignore"))


def add_ai_configs(
    repo_root: Path,
    frameworks: Sequence[AGENTS],
    include_common_scaffold: bool,
    add_all_touched_configs_to_gitignore: bool,
    add_vscode_task: bool,
    add_private_config: bool,
    add_instructions: bool,
) -> InitConfigResult:
    if len(frameworks) == 0:
        raise ValueError("At least one framework must be provided")

    started_at = perf_counter()
    repo_root_resolved = get_repo_root(repo_root)
    if repo_root_resolved is not None:
        repo_root = repo_root_resolved
    repo_root = repo_root.resolve()
    supported_frameworks = get_args(AGENTS)
    selected_frameworks: tuple[AGENTS, ...] = tuple(dict.fromkeys(frameworks))
    for framework in selected_frameworks:
        if framework not in supported_frameworks:
            raise ValueError(f"Unsupported framework: {framework}. The supported frameworks are: {', '.join(supported_frameworks)}")

    plan = InitConfigPlan(
        repo_root=repo_root,
        frameworks=selected_frameworks,
        include_common_scaffold=include_common_scaffold,
        add_all_touched_configs_to_gitignore=add_all_touched_configs_to_gitignore,
        add_vscode_task=add_vscode_task,
        add_private_config=add_private_config,
        add_instructions=add_instructions,
    )
    show_init_config_plan(plan=plan)

    with create_phase_status(label="Scanning current repository state", destination=str(repo_root)):
        phase_started = perf_counter()
        files_before_configuration = _snapshot_repo_files(repo_root=repo_root)
    show_phase_complete(label="Scanned current repository state", destination=str(repo_root), elapsed_seconds=perf_counter() - phase_started)

    if include_common_scaffold:
        destination = f"./{ai_script_paths.TYPE_CHECKING_SCRIPTS_DIRECTORY.as_posix()}"
        with create_phase_status(label="Installing shared validation scripts", destination=destination):
            phase_started = perf_counter()
            repo_root.joinpath(".ai").mkdir(parents=True, exist_ok=True)
            repo_root.joinpath(ai_script_paths.TYPE_CHECKING_SCRIPTS_DIRECTORY.parent).mkdir(parents=True, exist_ok=True)
            generic.create_dot_scripts(repo_root=repo_root)
        show_phase_complete(label="Installed shared validation scripts", destination=destination, elapsed_seconds=perf_counter() - phase_started)

    if add_vscode_task:
        destination = "./.vscode/tasks.json"
        with create_phase_status(label="Updating VS Code validation task", destination=destination):
            phase_started = perf_counter()
            add_lint_and_type_check_task(repo_root=repo_root)
        show_phase_complete(label="Updated VS Code validation task", destination=destination, elapsed_seconds=perf_counter() - phase_started)

    for framework in selected_frameworks:
        with create_phase_status(label=f"Configuring {framework}", destination="agent-specific repository files"):
            phase_started = perf_counter()
            build_framework_config(repo_root=repo_root, framework=framework, add_private_config=add_private_config, add_instructions=add_instructions)
        show_phase_complete(
            label=f"Configured {framework}", destination="agent-specific repository files", elapsed_seconds=perf_counter() - phase_started
        )

    with create_phase_status(label="Measuring filesystem changes", destination=str(repo_root)):
        phase_started = perf_counter()
        files_after_configuration = _snapshot_repo_files(repo_root=repo_root)
        configuration_changes = _collect_artifact_changes(before=files_before_configuration, after=files_after_configuration)
    show_phase_complete(label="Measured filesystem changes", destination=str(repo_root), elapsed_seconds=perf_counter() - phase_started)

    if add_all_touched_configs_to_gitignore:
        destination = "./.gitignore"
        with create_phase_status(label="Recording generated config paths", destination=destination):
            phase_started = perf_counter()
            dot_git_ignore_path = repo_root.joinpath(".gitignore")
            if dot_git_ignore_path.exists() is False:
                dot_git_ignore_path.touch()
            generic.adjust_gitignore(
                repo_root=repo_root, include_default_entries=False, extra_entries=_collect_gitignore_entries(changes=configuration_changes)
            )
            gitignore_stat = dot_git_ignore_path.stat()
            files_after_configuration[Path(".gitignore")] = (gitignore_stat.st_mtime_ns, gitignore_stat.st_size)
        show_phase_complete(label="Recorded generated config paths", destination=destination, elapsed_seconds=perf_counter() - phase_started)

    result = InitConfigResult(
        plan=plan,
        artifact_changes=_collect_artifact_changes(before=files_before_configuration, after=files_after_configuration),
        elapsed_seconds=perf_counter() - started_at,
    )
    show_init_config_result(result=result)
    return result
