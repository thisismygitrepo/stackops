from pathlib import Path

import typer


def _format_command(command: list[str]) -> str:
    import os

    if os.name == "nt":
        import subprocess

        return subprocess.list2cmdline(command)
    import shlex

    return shlex.join(command)


def build_scrape_command(
    *,
    url: str,
    output_path: str,
    selector: str | None = "article",
    wait_selector: str | None = "article",
    wait: int | None = 2000,
    timeout: int | None = 60000,
    enable_resources: bool = True,
    package_spec: str = "scrapling[shell]",
    uvx_executable: str = "uvx",
    extra_args: list[str] | None = None,
) -> list[str]:
    command = [
        uvx_executable,
        package_spec,
        "extract",
        "stealthy-fetch",
        url,
        output_path,
    ]

    if wait_selector is not None:
        command.extend(["--wait-selector", wait_selector])
    if wait is not None:
        command.extend(["--wait", str(wait)])
    if timeout is not None:
        command.extend(["--timeout", str(timeout)])
    if enable_resources:
        command.append("--enable-resources")
    if selector is not None:
        command.extend(["-s", selector])
    if extra_args:
        command.extend(extra_args)

    return command


def run_scrape(
    *,
    url: str,
    output_path: str,
    selector: str | None = "article",
    wait_selector: str | None = "article",
    wait: int | None = 2000,
    timeout: int | None = 60000,
    enable_resources: bool = True,
    package_spec: str = "scrapling[shell]",
    extra_args: list[str] | None = None,
) -> int:
    output = Path(output_path).expanduser()
    if str(output.parent) not in {"", "."}:
        output.parent.mkdir(parents=True, exist_ok=True)

    command = build_scrape_command(
        url=url,
        output_path=str(output),
        selector=selector,
        wait_selector=wait_selector,
        wait=wait,
        timeout=timeout,
        enable_resources=enable_resources,
        package_spec=package_spec,
        extra_args=extra_args,
    )

    typer.echo(_format_command(command))
    import subprocess

    try:
        completed = subprocess.run(command, check=False)
    except FileNotFoundError:
        typer.echo("Error: uvx command not found. Please install uv.", err=True)
        return 127

    return completed.returncode
