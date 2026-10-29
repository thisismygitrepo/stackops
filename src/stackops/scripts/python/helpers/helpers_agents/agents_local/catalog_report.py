from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.helpers.helpers_agents.agents_local.catalog import CatalogModel
from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import OLLAMA_CATALOG_URL, CatalogSort


def show_discovered_models(*, models: tuple[CatalogModel, ...], min_params: float, max_params: float, sort: CatalogSort) -> None:
    console = Console()
    console.print(Text(f"""Live Ollama catalog · advertised parameters {min_params:g}B–{max_params:g}B · {sort}""", style="bold cyan"))
    console.print(Text(f"""Source: {OLLAMA_CATALOG_URL}?sort={sort}""", style="dim"))
    console.print(Text("Catalog order reflects recency or popularity, not benchmark quality.", style="dim"))
    if not models:
        console.print(Text("No model families match these filters.", style="yellow"))
    else:
        table = Table(box=box.ROUNDED, header_style="bold cyan", show_lines=True)
        table.add_column("Model", ratio=2, overflow="fold")
        table.add_column("Sizes in range", overflow="fold")
        table.add_column("Download (GB)", justify="right", overflow="fold")
        table.add_column("Capabilities", overflow="fold")
        table.add_column("Pulls", justify="right")
        table.add_column("Updated", overflow="fold")
        for model in models:
            url = f"""{OLLAMA_CATALOG_URL}/{model.name}/tags"""
            label = Text(model.name, style=f"""bold link {url}""")
            download_sizes: list[str] = []
            for size in model.sizes:
                download = model.download_sizes_gb.get(size)
                if download is None:
                    download_sizes.append("—")
                elif download.minimum_gb == download.maximum_gb:
                    download_sizes.append(f"""{download.minimum_gb:g}""")
                else:
                    download_sizes.append(f"""{download.minimum_gb:g}–{download.maximum_gb:g}""")
            table.add_row(
                label, "\n".join(model.sizes), "\n".join(download_sizes),
                ", ".join(model.capabilities) or "-", model.pulls, model.updated or "-",
            )
        console.print(table)
    console.print(Text("Sizes are rounded catalog labels. Effective-only or unknown sizes, embedding models, and decision models are omitted.", style="dim"))
    console.print(Text("Download GB is for each default size tag; ranges vary by runtime. — means unavailable. Runtime memory varies with context.", style="dim"))
    console.print(Text("Open a model link for its downloadable tags; families may also offer cloud variants.", style="dim"))
