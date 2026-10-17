from typing import Annotated

import typer


def status(
    machine: Annotated[bool, typer.Option("--machine", "-m", help="Show the machine/system information section.")] = False,
    shell: Annotated[bool, typer.Option("--shell", "-s", help="Show the shell profile section.")] = False,
    repos: Annotated[bool, typer.Option("--repos", "-r", help="Show the configured repositories section.")] = False,
    ssh: Annotated[bool, typer.Option("--ssh", "-H", help="Show the SSH configuration section.")] = False,
    configs: Annotated[
        bool, typer.Option("--configs", "--dotfiles", "--symlinks", "-c", "-d", "-l", help="Show managed files, schemas, configuration mappings, and symlinks.")
    ] = False,
    apps: Annotated[bool, typer.Option("--apps", "--tools", "-a", "-t", help="Show the installed apps/tools section.")] = False,
    backup: Annotated[bool, typer.Option("--backup", "-b", help="Show the backup configuration section.")] = False,
    plain: Annotated[bool, typer.Option("--plain", "-p", help="Print a report instead of opening the interactive dashboard.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops import devops_status

    sections = devops_status.resolve_sections(machine=machine, shell=shell, repos=repos, ssh=ssh, configs=configs, apps=apps, backup=backup)
    devops_status.main(sections=sections, plain=plain)
