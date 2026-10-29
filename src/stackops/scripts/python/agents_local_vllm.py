from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import (
    VLLM_BIND_HOST,
    VLLM_DEFAULT_PORT,
    VLLM_INSTALL_PYTHON,
)


def _run_command(command: list[str], environment: dict[str, str] | None) -> None:
    import subprocess

    try:
        result = subprocess.run(command, env=environment, check=False)
    except KeyboardInterrupt:
        raise typer.Exit(code=130) from None
    except OSError as error:
        typer.echo(f"""Could not start {command[0]}: {error}""", err=True)
        raise typer.Exit(code=1) from error

    if result.returncode:
        raise typer.Exit(code=result.returncode if result.returncode > 0 else 128 - result.returncode)


def install() -> None:
    import platform
    import shutil
    import sys

    if sys.platform == "darwin":
        if platform.machine() != "arm64" or int(platform.mac_ver()[0].split(".")[0]) < 15:
            typer.echo("vLLM Metal requires Apple Silicon and macOS 15 or newer.", err=True)
            raise typer.Exit(code=1)
        brew = shutil.which("brew")
        if brew is None:
            typer.echo("Install Homebrew from https://brew.sh, then run agents local install again.", err=True)
            raise typer.Exit(code=1)
        typer.echo("Installing vLLM Metal with Homebrew...")
        _run_command(
            command=[brew, "tap", "vllm-project/vllm-metal", "https://github.com/vllm-project/vllm-metal"],
            environment=None,
        )
        _run_command(command=[brew, "install", "vllm-project/vllm-metal/vllm-metal"], environment=None)
    elif sys.platform == "linux":
        uv = shutil.which("uv")
        if uv is None:
            typer.echo("Install uv from https://docs.astral.sh/uv/getting-started/installation/, then run agents local install again.", err=True)
            raise typer.Exit(code=1)
        typer.echo("Installing vLLM for NVIDIA CUDA in an isolated uv tool environment...")
        _run_command(
            command=[uv, "tool", "install", "--python", VLLM_INSTALL_PYTHON, "--torch-backend", "auto", "vllm"],
            environment=None,
        )
    else:
        typer.echo("Install vLLM on Linux with NVIDIA CUDA or macOS 15+ with Apple Silicon. On Windows, run agents local install inside WSL2.", err=True)
        raise typer.Exit(code=1)

    typer.echo("vLLM installed. Start a model with: agents local serve MODEL")


def serve(
    ctx: typer.Context,
    model: Annotated[str, typer.Argument(help="Hugging Face model ID or local model directory to serve.")],
    host: Annotated[
        str,
        typer.Option("--host", "-H", help="Server bind address. Pass additional vLLM options after --."),
    ] = VLLM_BIND_HOST,
    port: Annotated[
        int,
        typer.Option("--port", "-p", min=1, max=65535, help="Server listening port."),
    ] = VLLM_DEFAULT_PORT,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", envvar="VLLM_API_KEY", show_default=False, hide_input=True, help="Require this API key for requests."),
    ] = None,
) -> None:
    import os
    import shutil
    import subprocess
    from pathlib import Path

    executable = shutil.which("vllm")
    if executable is None and (uv := shutil.which("uv")) is not None:
        try:
            result = subprocess.run([uv, "tool", "dir", "--bin"], capture_output=True, text=True, check=False)
        except OSError as error:
            typer.echo(f"""Could not locate uv-managed vLLM: {error}""", err=True)
            raise typer.Exit(code=1) from error
        if result.returncode:
            typer.echo(f"""Could not locate uv-managed vLLM: {result.stderr.strip()}""", err=True)
            raise typer.Exit(code=result.returncode if result.returncode > 0 else 128 - result.returncode)
        candidate = Path(result.stdout.strip()) / "vllm"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            executable = str(candidate)

    if executable is None:
        typer.echo("vLLM is not installed. Run agents local install first, or add your existing vllm executable to PATH.", err=True)
        raise typer.Exit(code=1)

    environment = os.environ.copy()
    if api_key is not None:
        environment["VLLM_API_KEY"] = api_key
    typer.echo(f"""Starting vLLM on {host}:{port}. Press Ctrl-C to stop.""")
    _run_command(
        command=[executable, "serve", model, "--host", host, "--port", str(port), *ctx.args],
        environment=environment,
    )
