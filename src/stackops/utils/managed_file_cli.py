import json
from pathlib import Path
from typing import Literal

import typer

from stackops.utils.managed_files import ManagedFileKind


def run_managed_file_action(*, kind: ManagedFileKind, action: Literal["path", "init", "validate"], path: Path | None) -> None:
    from stackops.utils.managed_file_operations import describe_managed_file, initialize_managed_file, validate_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    try:
        spec = get_managed_file_spec(kind)
        if path is not None:
            data_path = path.expanduser().absolute()
        elif kind in {"prompts", "parallel", "mcp"}:
            from stackops.utils.managed_agent_files import resolve_agent_managed_file_path

            data_path = resolve_agent_managed_file_path(kind=kind, source="repo")
        else:
            data_path = spec.user_path
        match action:
            case "path":
                typer.echo(json.dumps(describe_managed_file(spec=spec, data_path=data_path), indent=2))
            case "init":
                initialize_managed_file(spec=spec, data_path=data_path)
                typer.echo(json.dumps(describe_managed_file(spec=spec, data_path=data_path), indent=2))
            case "validate":
                validate_managed_file(kind=kind, data_path=data_path)
                typer.echo(f"""Valid {kind} file: {data_path}""")
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error
