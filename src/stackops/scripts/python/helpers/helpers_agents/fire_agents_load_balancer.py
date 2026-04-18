# from math import ceil
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_rich_output import show_chunking_panel


def chunk_prompts(prompt_material_path: Path, joiner: str, *, tasks_per_prompt: int) -> list[str]:
    """Chunk prompts based on splitting strategy.

    Args:
        prompts: List of prompts to chunk
        strategy: Either 'agent_cap' or 'task_rows'
        agent_cap: Maximum number of agents (used with 'agent_cap' strategy)
        task_rows: Number of rows/tasks per agent (used with 'task_rows' strategy)
    """
    prompts = [p for p in prompt_material_path.read_text(encoding="utf-8", errors="ignore").split(joiner) if p.strip() != ""]  # drop blank entries
    if tasks_per_prompt >= len(prompts):
        show_chunking_panel(
            subject="prompts",
            total_items=len(prompts),
            tasks_per_prompt=tasks_per_prompt,
            generated_agents=len(prompts),
            was_chunked=False,
        )
        return prompts
    grouped: list[str] = []
    for i in range(0, len(prompts), tasks_per_prompt):
        grouped.append(joiner.join(prompts[i : i + tasks_per_prompt]))
    show_chunking_panel(
        subject="prompts",
        total_items=len(prompts),
        tasks_per_prompt=tasks_per_prompt,
        generated_agents=len(grouped),
        was_chunked=True,
    )
    return grouped
