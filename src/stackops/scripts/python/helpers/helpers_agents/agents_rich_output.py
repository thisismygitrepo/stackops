from collections.abc import Sequence
from pathlib import Path
from typing import Final

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS, HOST, PROVIDER
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort

_CONSOLE: Final[Console] = Console()


def _repo_relative_path(*, path: Path, repo_root: Path) -> str:
    path_resolved = path.expanduser().resolve()
    repo_root_resolved = repo_root.expanduser().resolve()
    try:
        relative_path = path_resolved.relative_to(repo_root_resolved).as_posix()
    except ValueError:
        return str(path_resolved)
    if relative_path == ".":
        return str(repo_root_resolved)
    return f"./{relative_path}"


def _optional_label(*, value: str | None) -> str:
    if value is None or value == "":
        return "agent default"
    return value


def _file_name_or_placeholder(*, paths: Sequence[Path], placeholder: str) -> str:
    if len(paths) == 0:
        return placeholder
    return paths[0].name


def _files_summary(*, prompt_dir: Path) -> str:
    prompt_paths = sorted(prompt_dir.glob("*_prompt.txt"))
    material_paths = sorted(prompt_dir.glob("*_material.txt"))
    launcher_paths = sorted(prompt_dir.glob("*_cmd.sh"))
    return " | ".join(
        [
            _file_name_or_placeholder(paths=prompt_paths, placeholder="-"),
            _file_name_or_placeholder(paths=material_paths, placeholder="embedded"),
            _file_name_or_placeholder(paths=launcher_paths, placeholder="-"),
        ]
    )


def build_agents_create_overview_panel(
    *,
    repo_root: Path,
    agents_dir: Path,
    job_name: str,
    agent: AGENTS,
    host: HOST,
    provider: PROVIDER | None,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    agent_load: int,
    join_prompt_and_context: bool,
) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white", overflow="fold")
    table.add_row("Repository", str(repo_root.expanduser().resolve()))
    table.add_row("Agents dir", _repo_relative_path(path=agents_dir, repo_root=repo_root))
    table.add_row("Job", job_name)
    table.add_row("Agent", agent)
    table.add_row("Host", host)
    table.add_row("Provider", _optional_label(value=provider))
    table.add_row("Model", _optional_label(value=model))
    table.add_row("Reasoning", _optional_label(value=reasoning_effort))
    table.add_row("Rows per agent", str(agent_load))
    table.add_row("Prompt mode", "joined prompt/context" if join_prompt_and_context else "separate prompt/material")
    return Panel(table, title="Agent Create", border_style="blue")


def show_agents_create_overview(
    *,
    repo_root: Path,
    agents_dir: Path,
    job_name: str,
    agent: AGENTS,
    host: HOST,
    provider: PROVIDER | None,
    model: str | None,
    reasoning_effort: ReasoningEffort | None,
    agent_load: int,
    join_prompt_and_context: bool,
) -> None:
    _CONSOLE.print(
        build_agents_create_overview_panel(
            repo_root=repo_root,
            agents_dir=agents_dir,
            job_name=job_name,
            agent=agent,
            host=host,
            provider=provider,
            model=model,
            reasoning_effort=reasoning_effort,
            agent_load=agent_load,
            join_prompt_and_context=join_prompt_and_context,
        )
    )


def build_chunking_panel(
    *,
    subject: str,
    total_items: int,
    tasks_per_prompt: int,
    generated_agents: int,
    was_chunked: bool,
) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_row("Input", subject)
    table.add_row("Total items", str(total_items))
    table.add_row("Rows per agent", str(tasks_per_prompt))
    table.add_row("Generated agents", str(generated_agents))
    table.add_row("Status", "chunked" if was_chunked else "unchanged")
    return Panel(table, title="Chunking", border_style="cyan" if was_chunked else "yellow")


def show_chunking_panel(
    *,
    subject: str,
    total_items: int,
    tasks_per_prompt: int,
    generated_agents: int,
    was_chunked: bool,
) -> None:
    _CONSOLE.print(
        build_chunking_panel(
            subject=subject,
            total_items=total_items,
            tasks_per_prompt=tasks_per_prompt,
            generated_agents=generated_agents,
            was_chunked=was_chunked,
        )
    )


def build_generated_agents_table(*, repo_root: Path, prompt_dirs: Sequence[Path]) -> Table:
    table = Table(title=f"Generated Agents ({len(prompt_dirs)})", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Agent", style="bold cyan", no_wrap=True)
    table.add_column("Directory", style="white", overflow="fold")
    table.add_column("Files", style="white", overflow="fold")
    for prompt_dir in prompt_dirs:
        table.add_row(
            prompt_dir.name,
            _repo_relative_path(path=prompt_dir, repo_root=repo_root),
            _files_summary(prompt_dir=prompt_dir),
        )
    return table


def show_generated_agents_table(*, repo_root: Path, prompt_dirs: Sequence[Path]) -> None:
    _CONSOLE.print(build_generated_agents_table(repo_root=repo_root, prompt_dirs=prompt_dirs))


def build_created_artifacts_panel(
    *,
    repo_root: Path,
    agents_dir: Path,
    layout_output_path: Path,
    artifacts_dir: Path,
    recreate_script_path: Path,
    agent_count: int,
) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, show_header=False, expand=True)
    table.add_column("Field", style="bold green", no_wrap=True)
    table.add_column("Value", style="white", overflow="fold")
    table.add_row("Agents", str(agent_count))
    table.add_row("Prompts dir", _repo_relative_path(path=agents_dir / "prompts", repo_root=repo_root))
    table.add_row("Layout", _repo_relative_path(path=layout_output_path, repo_root=repo_root))
    table.add_row("Create inputs", _repo_relative_path(path=artifacts_dir, repo_root=repo_root))
    table.add_row("Recreate script", _repo_relative_path(path=recreate_script_path, repo_root=repo_root))
    return Panel(table, title="Created", border_style="green")


def show_created_artifacts_panel(
    *,
    repo_root: Path,
    agents_dir: Path,
    layout_output_path: Path,
    artifacts_dir: Path,
    recreate_script_path: Path,
    agent_count: int,
) -> None:
    _CONSOLE.print(
        build_created_artifacts_panel(
            repo_root=repo_root,
            agents_dir=agents_dir,
            layout_output_path=layout_output_path,
            artifacts_dir=artifacts_dir,
            recreate_script_path=recreate_script_path,
            agent_count=agent_count,
        )
    )
