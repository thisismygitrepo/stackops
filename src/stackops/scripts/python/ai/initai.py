from collections.abc import Sequence
from pathlib import Path
from time import perf_counter
from typing import get_args

import stackops.scripts.python.ai.scripts.paths as ai_script_paths
from stackops.scripts.python.ai.initai_artifacts import merge_artifact_changes, write_text_artifact
from stackops.scripts.python.ai.initai_frameworks import build_framework_config
from stackops.scripts.python.ai.initai_models import ArtifactChange, InitConfigPlan, InitConfigResult
from stackops.scripts.python.ai.initai_rich_output import create_phase_status, show_init_config_plan, show_init_config_result, show_phase_complete
from stackops.scripts.python.ai.utils import generic
from stackops.scripts.python.ai.utils.vscode_tasks import add_lint_and_type_check_task
from stackops.scripts.python.helpers.helpers_agents import agents_skill_stackops_backend
from stackops.scripts.python.helpers.helpers_agents.agents_skill_impl import AGENTOPS_SKILL_NAME, build_stackops_skill_folder_names
from stackops.utils.accessories import get_repo_root
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS

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
    add_agentops_skill: bool,
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
        add_agentops_skill=add_agentops_skill,
    )
    show_init_config_plan(plan=plan)
    changes: list[ArtifactChange] = []

    if include_common_scaffold:
        destination = f"./{ai_script_paths.TYPE_CHECKING_SCRIPTS_DIRECTORY.as_posix()}"
        with create_phase_status(label="Installing shared validation scripts", destination=destination):
            phase_started = perf_counter()
            repo_root.joinpath(".ai").mkdir(parents=True, exist_ok=True)
            repo_root.joinpath(ai_script_paths.TYPE_CHECKING_SCRIPTS_DIRECTORY.parent).mkdir(parents=True, exist_ok=True)
            changes.extend(generic.create_dot_scripts(repo_root=repo_root))
        show_phase_complete(label="Installed shared validation scripts", destination=destination, elapsed_seconds=perf_counter() - phase_started)

    if add_vscode_task:
        destination = "./.vscode/tasks.json"
        with create_phase_status(label="Updating VS Code validation task", destination=destination):
            phase_started = perf_counter()
            changes.append(add_lint_and_type_check_task(repo_root=repo_root))
        show_phase_complete(label="Updated VS Code validation task", destination=destination, elapsed_seconds=perf_counter() - phase_started)

    for framework in selected_frameworks:
        with create_phase_status(label=f"Configuring {framework}", destination="agent-specific repository files"):
            phase_started = perf_counter()
            changes.extend(
                build_framework_config(
                    repo_root=repo_root,
                    framework=framework,
                    add_private_config=add_private_config,
                    add_instructions=add_instructions,
                )
            )
        show_phase_complete(
            label=f"Configured {framework}", destination="agent-specific repository files", elapsed_seconds=perf_counter() - phase_started
        )

    if add_agentops_skill:
        destination = "./.agents/skills/agentops"
        with create_phase_status(label="Copying latest bundled AgentOps skill", destination=destination):
            phase_started = perf_counter()
            install_results = agents_skill_stackops_backend.install_stackops_agent_skills(
                skill_names=(AGENTOPS_SKILL_NAME,),
                skill_folder_names=build_stackops_skill_folder_names(),
                install_root=repo_root,
                scope="local",
            )
            for install_result in install_results:
                changes.extend(
                    ArtifactChange(path=path.relative_to(repo_root), action="created")
                    for path in install_result.created_paths
                )
                changes.extend(
                    ArtifactChange(path=path.relative_to(repo_root), action="written")
                    for path in install_result.written_paths
                )
        show_phase_complete(label="Copied latest bundled AgentOps skill", destination=destination, elapsed_seconds=perf_counter() - phase_started)

    configuration_changes = merge_artifact_changes(changes=changes)

    if add_all_touched_configs_to_gitignore:
        destination = "./.gitignore"
        with create_phase_status(label="Recording generated config paths", destination=destination):
            phase_started = perf_counter()
            dot_git_ignore_path = repo_root.joinpath(".gitignore")
            gitignore_change = write_text_artifact(
                repo_root=repo_root,
                path=dot_git_ignore_path,
                content="",
                write_mode="if_missing",
            )
            gitignore_written = generic.adjust_gitignore(
                repo_root=repo_root, include_default_entries=False, extra_entries=_collect_gitignore_entries(changes=configuration_changes)
            )
            if gitignore_change is not None:
                changes.append(gitignore_change)
            elif gitignore_written:
                changes.append(ArtifactChange(path=Path(".gitignore"), action="written"))
        show_phase_complete(label="Recorded generated config paths", destination=destination, elapsed_seconds=perf_counter() - phase_started)

    result = InitConfigResult(
        plan=plan,
        artifact_changes=merge_artifact_changes(changes=changes),
        elapsed_seconds=perf_counter() - started_at,
    )
    show_init_config_result(result=result)
    return result
