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
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print structured section results.")] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops import devops_status

    sections = devops_status.resolve_sections(machine=machine, shell=shell, repos=repos, ssh=ssh, configs=configs, apps=apps, backup=backup)
    if json_output:
        import json
        import sys
        from contextlib import redirect_stdout
        from stackops.scripts.python.helpers.helpers_devops.devops_status_data import collect_status_section

        with redirect_stdout(sys.stderr):
            snapshots = {section: collect_status_section(section) for section in sections}
        typer.echo(json.dumps({section: {"summary": snapshot.summary, "level": snapshot.level, "details": snapshot.details} for section, snapshot in snapshots.items()}, default=_serialize_status_value))
        if any(snapshot.level == "error" for snapshot in snapshots.values()):
            raise typer.Exit(code=1)
        return
    devops_status.main(sections=sections, plain=plain)


def _serialize_status_value(value: object) -> object:
    from dataclasses import fields, is_dataclass
    from datetime import date, datetime
    from pathlib import Path

    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (set, frozenset)):
        return sorted(value)
    raise TypeError(f"""Cannot serialize status value of type {type(value).__name__}""")
