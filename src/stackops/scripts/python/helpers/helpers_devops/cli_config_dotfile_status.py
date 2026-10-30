from typing import Annotated

import typer

STATUS_HELP = "Show read-only dotfile stats: mappers, sync state, known dotfiles not in your mapper, and storage."


def show_dotfiles_status(
    mappers: Annotated[bool, typer.Option("--mappers", "-m", help="Show mapper sizes per OS.")] = False,
    sync: Annotated[bool, typer.Option("--sync", "-s", help="Show the sync state of your mapped entries and the library's on this machine.")] = False,
    radar: Annotated[bool, typer.Option("--radar", "-r", help="Show known dotfiles found on this machine, by what collect would do with them.")] = False,
    storage: Annotated[bool, typer.Option("--storage", "-d", help="Show disk usage of ~/dotfiles and your managed copies, entries export misses, and unreferenced stored files.")] = False,
    expand: Annotated[bool, typer.Option("--expand", "-e", help="List every entry in the shown sections instead of summaries.")] = False,
    which: Annotated[
        str | None,
        typer.Option("--which", "-w", help="Only these groups, comma-separated. The ~/dotfiles total and unreferenced stored files stay global."),
    ] = None,
) -> None:
    import platform

    from rich.console import Console
    from rich.text import Text

    from stackops.profile.create_links import normalize_os_name
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_data import (
        collect_mappers_status,
        collect_radar_status,
        collect_storage_status,
        collect_sync_status,
        load_mappers,
    )
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_render import render_mappers, render_storage, render_sync
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_render_radar import render_radar

    show_all = not (mappers or sync or radar or storage)
    current_os = normalize_os_name(platform.system())
    loaded_mappers = load_mappers()
    console = Console()
    groups: frozenset[str] | None = None
    if which is not None:
        requested_groups = [item.strip() for item in which.split(",")]
        known_groups = {*loaded_mappers.user, *loaded_mappers.library, *loaded_mappers.catalog}
        unknown_groups = [group for group in requested_groups if group not in known_groups]
        if len(unknown_groups) > 0:
            typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"""Unknown --which group(s): {", ".join(repr(group) for group in unknown_groups)}. Known groups: {", ".join(sorted(known_groups))}""")
            raise typer.Exit(code=1)
        groups = frozenset(requested_groups)
        console.print(Text(f"""Groups: {", ".join(requested_groups)}""", style="dim"))
    if show_all or mappers:
        console.print(render_mappers(collect_mappers_status(loaded_mappers, groups), expand=expand))
    if show_all or sync:
        console.print(render_sync(collect_sync_status(loaded_mappers, groups, current_os), current_os=current_os, expand=expand))
    if show_all or radar:
        console.print(render_radar(collect_radar_status(loaded_mappers, groups, current_os), current_os=current_os, expand=expand))
    if show_all or storage:
        console.print(render_storage(collect_storage_status(loaded_mappers, groups), expand=expand))
