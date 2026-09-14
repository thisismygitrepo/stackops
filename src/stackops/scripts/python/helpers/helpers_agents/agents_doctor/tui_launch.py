import subprocess
import sys
from typing import Literal

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_models import CleanupScope


def launch_agent_tui(
    *,
    mode: Literal["doctor", "depoison"],
    agent: str,
    directory: str,
    resource: str,
    scope: CleanupScope,
    match: str | None,
    recursive: bool,
) -> None:
    from stackops.utils.meta import lambda_to_python_script

    worker_source = lambda_to_python_script(
        lambda: _run_agent_tui(
            mode=mode,
            agent=agent,
            directory=directory,
            resource=resource,
            scope=scope,
            match=match,
            recursive=recursive,
        ),
        in_global=True,
        import_module=False,
    )
    command = ["uv", "run", "--no-project", "--python", sys.executable, "--with", "textual"]
    if mode == "depoison":
        command.extend(["--with", "tomlkit"])
    command.extend(["python", "-c", worker_source])
    result = subprocess.run(command, check=False)
    raise typer.Exit(code=result.returncode)


def _run_agent_tui(
    *,
    mode: Literal["doctor", "depoison"],
    agent: str,
    directory: str,
    resource: str,
    scope: CleanupScope,
    match: str | None,
    recursive: bool,
) -> None:
    import typer

    try:
        if mode == "doctor":
            from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_doctor import run_doctor_tui

            run_doctor_tui(requested_agent=agent, directory=directory, requested_resources=resource)
        else:
            from stackops.scripts.python.helpers.helpers_agents.agents_doctor.tui_depoison import run_depoison_tui

            run_depoison_tui(agent=agent, directory=directory, scope=scope, resource=resource, match=match, recursive=recursive)
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise SystemExit(2) from error
