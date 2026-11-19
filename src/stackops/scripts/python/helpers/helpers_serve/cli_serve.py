import typer


def serve(host: str, port: int, open_browser: bool) -> None:
    import os
    import platform
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    from stackops.scripts.python.helpers.helpers_serve.constants import (
        LAUNCH_PATH_VARIABLE,
        LAUNCH_VIRTUAL_ENV_VARIABLE,
        SERVER_RUNTIME_DEPENDENCIES,
        WINDOWS_PTY_DEPENDENCY,
    )

    stackops_executable = shutil.which("stackops", path=str(Path(sys.executable).parent))
    if stackops_executable is None:
        raise typer.BadParameter(f"""The web UI runs commands through the `stackops` executable, and none sits next to {sys.executable}.""")
    dependencies = [*SERVER_RUNTIME_DEPENDENCIES, *([WINDOWS_PTY_DEPENDENCY] if platform.system() == "Windows" else [])]
    worker_source = f"""from stackops.scripts.python.helpers.helpers_serve.server_main import run_server
run_server(host={host!r}, port={port!r}, open_browser={open_browser!r}, stackops_executable={stackops_executable!r}, working_directory={str(Path.cwd())!r})
"""
    command = ["uv", "run", "--no-project", "--python", sys.executable]
    for dependency in dependencies:
        command.extend(["--with", dependency])
    command.extend(["python", "-c", worker_source])
    environment = {**os.environ, LAUNCH_PATH_VARIABLE: os.environ["PATH"], LAUNCH_VIRTUAL_ENV_VARIABLE: os.environ.get("VIRTUAL_ENV", "")}
    server = subprocess.Popen(command, env=environment)
    try:
        return_code = server.wait()
    except KeyboardInterrupt:  # Ctrl+C reaches the server too; wait for it to stop its running commands.
        return_code = server.wait()
    raise typer.Exit(code=return_code)
