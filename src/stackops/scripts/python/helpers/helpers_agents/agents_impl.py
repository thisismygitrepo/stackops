"""Pure Python implementations for agents commands - no typer dependencies."""

from contextlib import nullcontext
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Literal

from stackops.utils.schemas.fire_agents.fire_agents_types import (
    AGENTS,
    CONFIG_AGENTS,
    CONFIG_AGENT_VALUES,
    HOST,
    PROVIDER,
    ReasoningEffort,
)
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import normalize_reasoning_effort


AgentsDirectoryConflict = Literal["error", "new-directory", "replace-owned"]


@dataclass(frozen=True, slots=True)
class AgentCreationResult:
    agents_dir: Path
    layout_path: Path
    artifacts_dir: Path
    agent_count: int
    launched: bool


def agents_create(
    agent: AGENTS,
    model: str | None,
    agent_load: int,
    context: str | None,
    context_path: str | None,
    separator: str,
    prompt: str | None,
    prompt_path: str | None,
    prompt_name: str | None,
    job_name: str | None,
    join_prompt_and_context: bool,
    output_path: str | None,
    agents_dir: str | None,
    host: HOST,
    reasoning: ReasoningEffort | None,
    provider: PROVIDER | None,
    on_directory_conflict: AgentsDirectoryConflict,
    stagger_max: float,
) -> AgentCreationResult:
    """Split the context across agents and write their prompts, launchers and layout file."""
    normalized_reasoning_effort = normalize_reasoning_effort(agent=agent, reasoning_effort=reasoning)
    if not isfinite(stagger_max) or stagger_max < 0:
        raise ValueError("stagger_max must be a finite number greater than or equal to 0")
    from stackops.scripts.python.helpers.helpers_agents.agents_create_artifacts import (
        CreateContextArtifactsInput,
        CreatePromptArtifactsInput,
        write_create_artifacts,
    )
    from stackops.scripts.python.helpers.helpers_agents.agents_create_inputs import (
        resolve_context_input,
        resolve_agents_layout_path,
        resolve_agents_output_dir,
        resolve_agents_workspace_root,
        resolve_prompt_input,
        validate_agents_output_dir_cleanup,
    )
    from stackops.scripts.python.helpers.helpers_agents.agents_create_replacement import replace_owned_job
    from stackops.scripts.python.helpers.helpers_agents.fire_agents_help_launch import (
        get_agents_launch_layout,
        get_prompt_directories,
        prep_agent_launch,
        validate_agent_host,
    )
    from stackops.scripts.python.helpers.helpers_agents.agents_rich_output import (
        show_agents_create_overview,
        show_created_artifacts_panel,
        show_generated_agents_table,
    )
    from stackops.utils.repos.project import resolve_project_root
    from stackops.utils.schemas.layouts.layout_file import require_layout_suffix, write_layouts_file

    validate_agent_host(agent=agent, host=host)
    project_root = resolve_project_root(current_dir=Path.cwd())
    repo_root = Path.cwd().resolve() if project_root is None else project_root.resolve()

    if agent == "codex":
        if provider is None:
            provider = "openai"
        elif provider != "openai":
            raise ValueError("Codex agent only works with openai provider.")

    requested_job_dir, job_name_resolved = resolve_agents_output_dir(repo_root=repo_root, agents_dir=agents_dir, job_name=job_name)
    del job_name
    agents_dir_obj = requested_job_dir
    directory_conflict = agents_dir_obj.exists()
    cleanup_existing_agents_dir = False
    while True:
        if directory_conflict:
            match on_directory_conflict:
                case "error":
                    raise ValueError(f"Agents directory already exists: {agents_dir_obj}. Pass --on-directory-conflict new-directory or replace-owned.")
                case "new-directory":
                    from uuid import uuid4

                    agents_dir_obj = requested_job_dir.with_name(f"{requested_job_dir.name}-{uuid4().hex[:12]}")
                case "replace-owned":
                    validate_agents_output_dir_cleanup(repo_root=repo_root, agents_dir_obj=agents_dir_obj)
                    cleanup_existing_agents_dir = True

        layout_output_path = resolve_agents_layout_path(agents_dir=agents_dir_obj, output_path=output_path)
        require_layout_suffix(layout_output_path)
        prompt_input = resolve_prompt_input(prompt=prompt, prompt_path=prompt_path, prompt_name=prompt_name)
        context_input = resolve_context_input(
            context=context, context_path=context_path, separator=separator, agent_load=agent_load, agents_dir_obj=agents_dir_obj
        )
        if cleanup_existing_agents_dir:
            break
        try:
            agents_dir_obj.mkdir(parents=True)
        except FileExistsError:
            directory_conflict = True
            continue
        break
    workspace_root = resolve_agents_workspace_root(preferred_root=repo_root, agents_dir_obj=agents_dir_obj)
    del agents_dir

    show_agents_create_overview(
        repo_root=workspace_root,
        agents_dir=agents_dir_obj,
        job_name=job_name_resolved,
        agent=agent,
        host=host,
        provider=provider,
        model=model,
        reasoning_effort=normalized_reasoning_effort,
        agent_load=agent_load,
        stagger_max=stagger_max,
        join_prompt_and_context=join_prompt_and_context,
    )

    destination = (
        replace_owned_job(repo_root=repo_root, agents_dir=agents_dir_obj, layout_path=layout_output_path)
        if cleanup_existing_agents_dir
        else nullcontext(layout_output_path)
    )
    with destination as layout_write_path:
        prep_agent_launch(
            repo_root=workspace_root,
            agents_dir=agents_dir_obj,
            prompts_material=context_input.prompt_materials,
            material_suffix=context_input.material_suffix,
            join_prompt_and_context=join_prompt_and_context,
            prompt_prefix=prompt_input.prompt_text,
            machine=host,
            agent=agent,
            model=model,
            reasoning_effort=normalized_reasoning_effort,
            provider=provider,
            job_name=job_name_resolved,
            stagger_max=stagger_max,
        )
        prompt_directories = get_prompt_directories(prompt_root=agents_dir_obj / "prompts")
        show_generated_agents_table(repo_root=workspace_root, prompt_dirs=prompt_directories)
        layoutfile = get_agents_launch_layout(session_root=agents_dir_obj, job_name=job_name_resolved, start_dir=workspace_root)
        write_layouts_file(path=layout_write_path, layouts_file=layoutfile)
        create_artifacts = write_create_artifacts(
            repo_root=workspace_root,
            agents_dir=agents_dir_obj,
            layout_output_path=layout_output_path,
            agent=agent,
            host=host,
            model=model,
            reasoning_effort=normalized_reasoning_effort,
            provider=provider,
            agent_load=agent_load,
            stagger_max=stagger_max,
            separator=separator,
            prompt=CreatePromptArtifactsInput(
                source_kind=prompt_input.source_kind,
                source_path=prompt_input.source_path,
                source_name=prompt_input.source_name,
                content=prompt_input.prompt_text,
            ),
            context=CreateContextArtifactsInput(
                source_kind=context_input.source_kind,
                source_path=context_input.source_path,
                file_content=context_input.file_content,
                directory_entries=context_input.directory_entries,
            ),
            job_name=job_name_resolved,
            join_prompt_and_context=join_prompt_and_context,
        )
    show_created_artifacts_panel(
        repo_root=workspace_root,
        agents_dir=agents_dir_obj,
        layout_output_path=layout_output_path,
        artifacts_dir=create_artifacts.artifacts_dir,
        agent_count=len(prompt_directories),
    )
    return AgentCreationResult(
        agents_dir=agents_dir_obj,
        layout_path=layout_output_path,
        artifacts_dir=create_artifacts.artifacts_dir,
        agent_count=len(prompt_directories),
        launched=False,
    )


def init_config(
    root: str | None,
    frameworks: tuple[CONFIG_AGENTS, ...],
    include_common: bool,
    add_all_configs_to_gitignore: bool,
    add_lint_task: bool,
    add_config: bool,
    add_instructions: bool,
    add_agent_ops_skill: bool,
) -> None:
    """Initialize AI configurations in the current repository."""
    from stackops.scripts.python.ai.initai import add_ai_configs

    if root is None:
        repo_root = Path.cwd()
    else:
        repo_root = Path(root).expanduser().resolve()
    if len(frameworks) > 0:
        selected_frameworks_list: list[CONFIG_AGENTS] = []
        for framework in frameworks:
            if framework not in CONFIG_AGENT_VALUES:
                raise ValueError(
                    f"Unsupported framework: {framework}. The supported frameworks are: {', '.join(CONFIG_AGENT_VALUES)}"
                )
            selected_frameworks_list.append(framework)
        selected_frameworks: tuple[CONFIG_AGENTS, ...] = tuple(dict.fromkeys(selected_frameworks_list))
    else:
        raise ValueError("Provide at least one --framework option, or pass --all-frameworks")

    add_ai_configs(
        repo_root=repo_root,
        frameworks=selected_frameworks,
        include_common_scaffold=include_common,
        add_all_touched_configs_to_gitignore=add_all_configs_to_gitignore,
        add_vscode_task=add_lint_task,
        add_private_config=add_config,
        add_instructions=add_instructions,
        add_agent_ops_skill=add_agent_ops_skill,
    )


# def main() -> None:
#     a = 2
#     del a
#     print(a)
