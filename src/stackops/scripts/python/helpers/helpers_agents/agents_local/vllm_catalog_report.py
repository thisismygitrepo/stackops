from shlex import quote

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import HUGGING_FACE_HUB_URL, VLLM_CATALOG_URL, CatalogSort
from stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_catalog import VllmCatalogModel


def show_discovered_vllm_models(*, models: tuple[VllmCatalogModel, ...], min_params: float, max_params: float, sort: CatalogSort) -> None:
    console = Console()
    console.print(Text(f"""Hugging Face vLLM catalog · reported parameters {min_params:g}B–{max_params:g}B · {sort}""", style="bold cyan"))
    console.print(Text(f"""Source: {VLLM_CATALOG_URL}""", style="dim"))
    console.print(Text("Newest sorts by repository creation; popular sorts by downloads. Neither measures model quality.", style="dim"))
    if not models:
        console.print(Text("No models match these filters.", style="yellow"))
    else:
        table = Table(box=box.ROUNDED, header_style="bold cyan", show_lines=True)
        table.add_column("Model", ratio=2, overflow="fold")
        table.add_column("Parameters (B)", justify="right")
        table.add_column("Task", overflow="fold")
        table.add_column("Downloads", justify="right")
        table.add_column("Updated", overflow="fold")
        for model in models:
            url = f"""{HUGGING_FACE_HUB_URL}/{model.name}"""
            table.add_row(
                Text(model.name, style=f"""bold link {url}"""),
                f"""{model.parameters / 1e9:.3g}""",
                model.task,
                f"""{model.downloads:,}""",
                model.updated.partition("T")[0],
            )
        console.print(table)
        console.print(Text(f"""Start a model: agents local serve {quote(models[0].name)}""", style="cyan"))
    console.print(Text("Counts use Hugging Face safetensors metadata; models with unknown counts are omitted. Runtime memory varies with context.", style="dim"))
    console.print(Text("Hugging Face lists these models for vLLM. Check the model card and your installed vLLM version and hardware before serving.", style="dim"))
