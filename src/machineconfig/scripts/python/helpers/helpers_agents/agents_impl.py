"""Pure Python implementations for agents commands - no typer dependencies."""

from pathlib import Path
from time import perf_counter

from machineconfig.scripts.python.helpers.helpers_agents.agents_create_artifacts import (
    CreateContextArtifactsInput,
    CreatePromptArtifactsInput,
    write_create_artifacts,
)
from machineconfig.scripts.python.helpers.helpers_agents.agents_create_inputs import (
    resolve_context_input,
    resolve_agents_output_dir,
    resolve_prompt_input,
)
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from machineconfig.scripts.python.helpers.helpers_agents.agents_rich_output import (
    show_agents_create_overview,
    show_created_artifacts_panel,
    show_generated_agents_table,
)
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort
import machineconfig.scripts.python.helpers.helpers_agents.templates as template_assets
from machineconfig.utils.path_reference import get_path_reference_path


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
    reasoning_effort: ReasoningEffort | None,
    provider: PROVIDER | None,

    interactive: bool,
) -> None:
    """Create agents layout file, ready to run."""
    if interactive:
        from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive.main import main
        main(
            agent=agent,
            host=host,
            model=model,
            reasoning_effort=reasoning_effort,
            provider=provider,
            agent_load=agent_load,
            context=context,
            context_path=context_path,
            separator=separator,
            prompt=prompt,
            prompt_path=prompt_path,
            prompt_name=prompt_name,
            job_name=job_name,
            join_prompt_and_context=join_prompt_and_context,
            output_path=output_path,
            agents_dir=agents_dir,
        )
        return
    from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_help_launch import (
        get_agents_launch_layout,
        get_prompt_directories,
        prep_agent_launch,
    )
    from machineconfig.utils.accessories import get_repo_root
    import json

    if agent != "codex" and reasoning_effort is not None:
        raise ValueError("--reasoning-effort is only supported for --agent codex")

    repo_root = get_repo_root(Path.cwd())
    if repo_root is None:
        raise RuntimeError("💥 Could not determine the repository root. Please run this script from within a git repository.")

    if agent == "codex":
        if provider is None:
            provider = "openai"
        elif provider != "openai":
            raise ValueError("Codex agent only works with openai provider.")

    agents_dir_obj, job_name_resolved = resolve_agents_output_dir(
        repo_root=repo_root,
        agents_dir=agents_dir,
        job_name=job_name,
    )
    del job_name
    cleanup_existing_agents_dir = agents_dir is not None and agents_dir_obj.exists()
    del agents_dir

    show_agents_create_overview(
        repo_root=repo_root,
        agents_dir=agents_dir_obj,
        job_name=job_name_resolved,
        agent=agent,
        host=host,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        agent_load=agent_load,
        join_prompt_and_context=join_prompt_and_context,
    )

    prompt_input = resolve_prompt_input(prompt=prompt, prompt_path=prompt_path, prompt_name=prompt_name)
    context_input = resolve_context_input(
        context=context,
        context_path=context_path,
        separator=separator,
        agent_load=agent_load,
        agents_dir_obj=agents_dir_obj,
    )

    if cleanup_existing_agents_dir:
        import shutil

        shutil.rmtree(agents_dir_obj)

    agent_selected = agent
    prep_agent_launch(
        repo_root=repo_root,
        agents_dir=agents_dir_obj,
        prompts_material=context_input.prompt_materials,
        join_prompt_and_context=join_prompt_and_context,
        prompt_prefix=prompt_input.prompt_text,
        machine=host,
        agent=agent_selected,
        model=model,
        reasoning_effort=reasoning_effort,
        provider=provider,
        job_name=job_name_resolved,
    )
    prompt_directories = get_prompt_directories(prompt_root=agents_dir_obj / "prompts")
    show_generated_agents_table(repo_root=repo_root, prompt_dirs=prompt_directories)
    layoutfile = get_agents_launch_layout(session_root=agents_dir_obj, job_name=job_name_resolved)

    layout_output_path = Path(output_path) if output_path is not None else agents_dir_obj / "layout.json"
    layout_output_path.parent.mkdir(parents=True, exist_ok=True)
    layout_output_path.write_text(data=json.dumps(layoutfile, indent=4), encoding="utf-8")
    create_artifacts = write_create_artifacts(
        repo_root=repo_root,
        agents_dir=agents_dir_obj,
        layout_output_path=layout_output_path.resolve(),
        agent=agent_selected,
        host=host,
        model=model,
        reasoning_effort=reasoning_effort,
        provider=provider,
        agent_load=agent_load,
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
        repo_root=repo_root,
        agents_dir=agents_dir_obj,
        layout_output_path=layout_output_path.resolve(),
        artifacts_dir=create_artifacts.artifacts_dir,
        recreate_script_path=create_artifacts.recreate_script_path,
        agent_count=len(prompt_directories),
    )


def collect(agent_dir: str, output_path: str, separator: str, pattern: str | None) -> None:
    """Collect all material files from an agent directory and concatenate them."""
    if not Path(agent_dir).exists() or not Path(agent_dir).is_dir():
        raise ValueError(f"Agent directory does not exist or is not a directory: {agent_dir}")

    prompts_dir = Path(agent_dir) / "prompts"
    if not prompts_dir.exists():
        raise ValueError(f"Prompts directory not found: {prompts_dir}")

    material_files: list[Path] = []
    for agent_subdir in prompts_dir.iterdir():
        if pattern is None:
            if agent_subdir.is_dir() and agent_subdir.name.startswith("agent_"):
                material_file = agent_subdir / f"{agent_subdir.name}_material.txt"
                if material_file.exists():
                    material_files.append(material_file)
        else:
            if agent_subdir.is_dir():
                for material_file in agent_subdir.glob(pattern):
                    if material_file.is_file():
                        material_files.append(material_file)

    if not material_files:
        print("No material files found in the agent directory.")
        return
    print(f"Found {len(material_files)} material files. Concatenating...")
    for idx, a_file in enumerate(material_files):
        print(f"{idx+1}. {a_file}")
    material_files.sort(key=lambda x: int(x.parent.name.split("_")[-1]))
    concatenated_content: list[str] = []
    for material_file in material_files:
        content = material_file.read_text(encoding="utf-8")
        concatenated_content.append(content)
    result = separator.join(concatenated_content)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(result, encoding="utf-8")
    print(f"Concatenated material written to {output_path}")


def make_agents_command_template() -> None:
    """Create a template for fire agents."""
    from platform import system

    if system() == "Linux" or system() == "Darwin":
        template_path = get_path_reference_path(
            module=template_assets,
            path_reference=template_assets.TEMPLATE_SH_PATH_REFERENCE,
        )
    elif system() == "Windows":
        template_path = get_path_reference_path(
            module=template_assets,
            path_reference=template_assets.TEMPLATE_PS1_PATH_REFERENCE,
        )
    else:
        raise ValueError(f"Unsupported OS: {system()}")

    from machineconfig.utils.accessories import get_repo_root
    repo_root = get_repo_root(Path.cwd())
    if repo_root is None:
        raise RuntimeError("💥 Could not determine the repository root. Please run this script from within a git repository.")

    save_path_root = repo_root / ".ai" / "agents" / "template"
    save_path_root.mkdir(parents=True, exist_ok=True)
    save_path_root.joinpath("template_fire_agents.sh").write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Template bash script written to {save_path_root}")

    from machineconfig.scripts.python.ai.utils.generate_files import make_todo_files
    make_todo_files(
        pattern=".py", repo=str(repo_root), strategy="name", output_path=str(save_path_root / "files.md"), split_every=None, split_to=None
    )

    prompt_path = get_path_reference_path(
        module=template_assets,
        path_reference=template_assets.PROMPT_PATH_REFERENCE,
    )
    save_path_root.joinpath("prompt.txt").write_text(prompt_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Prompt template written to {save_path_root}")


def init_config(
    root: str | None,
    frameworks: tuple[AGENTS, ...],
    include_common: bool,
    add_all_configs_to_gitignore: bool,
    add_lint_task: bool,
    add_config: bool,
    add_instructions: bool,
) -> None:
    """Initialize AI configurations in the current repository."""
    from machineconfig.scripts.python.ai.initai import add_ai_configs
    started_at = perf_counter()
    print("[init-config] Starting configuration")
    if root is None:
        repo_root = Path.cwd()
    else:
        repo_root = Path(root).expanduser().resolve()
    print(f"[init-config] Repository root input: {repo_root}")
    from typing import get_args
    if len(frameworks) > 0:
        selected_frameworks_list: list[AGENTS] = []
        for framework in frameworks:

            if framework not in get_args(AGENTS):
                raise ValueError(f"Unsupported framework: {framework}. The supported frameworks are: {', '.join(get_args(AGENTS))}")
            selected_frameworks_list.append(framework)
        selected_frameworks: tuple[AGENTS, ...] = tuple(dict.fromkeys(selected_frameworks_list))
        print(f"[init-config] Selected frameworks: {', '.join(selected_frameworks)}")
    else:
        raise ValueError("Provide at least one --framework option, or pass --all-frameworks")

    before_add_configs = perf_counter()
    print("[init-config] Running add_ai_configs")
    add_ai_configs(
        repo_root=repo_root,
        frameworks=selected_frameworks,
        include_common_scaffold=include_common,
        add_all_touched_configs_to_gitignore=add_all_configs_to_gitignore,
        add_vscode_task=add_lint_task,
        add_private_config=add_config,
        add_instructions=add_instructions,
    )
    add_configs_elapsed = perf_counter() - before_add_configs
    total_elapsed = perf_counter() - started_at
    print(f"[init-config] add_ai_configs finished in {add_configs_elapsed:.3f}s")
    print(f"[init-config] Completed in {total_elapsed:.3f}s")


# def main() -> None:
#     a = 2
#     del a
#     print(a)
