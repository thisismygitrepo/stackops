STATUS_HELP = "Show read-only dotfile stats: mappers, sync state, known dotfiles not in your mapper, and storage."


def show_dotfiles_status() -> None:
    import platform

    from rich.console import Console

    from stackops.profile.create_links import normalize_os_name
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_data import collect_dotfiles_status
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_status_render import render_mappers, render_radar, render_storage, render_sync

    status = collect_dotfiles_status(normalize_os_name(platform.system()))
    console = Console()
    for panel in (render_mappers(status), render_sync(status), render_radar(status), render_storage(status)):
        console.print(panel)
