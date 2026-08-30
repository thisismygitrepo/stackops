import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.ai.scripts.models_config import build_uv_tool_command


@dataclass(frozen=True, slots=True)
class ToolVersionSpec:
    title: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ToolVersionResult:
    spec: ToolVersionSpec
    version: str


class ToolVersionResolutionError(RuntimeError):
    pass


def build_tool_version_specs(latest: bool) -> tuple[ToolVersionSpec, ...]:
    return (
        ToolVersionSpec(
            title="Cleanpy",
            command=(
                *build_uv_tool_command(package="cleanpy", latest=latest),
                "-m",
                "cleanpy",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Ruff",
            command=(
                *build_uv_tool_command(package="ruff", latest=latest),
                "ruff",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Pyright",
            command=(
                *build_uv_tool_command(package="pyright", latest=latest),
                "pyright",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="MyPy",
            command=(
                *build_uv_tool_command(package="mypy", latest=latest),
                "mypy",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Pylint",
            command=(
                *build_uv_tool_command(package="pylint", latest=latest),
                "pylint",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Pyrefly",
            command=(
                *build_uv_tool_command(package="pyrefly", latest=latest),
                "pyrefly",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Ty",
            command=(
                *build_uv_tool_command(package="ty", latest=latest),
                "ty",
                "--version",
            ),
        ),
    )


def _resolve_tool_version(
    spec: ToolVersionSpec,
    subprocess_environment: dict[str, str],
) -> ToolVersionResult:
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            spec.command,
            env=subprocess_environment,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ToolVersionResolutionError(
            f"{spec.title} version command could not start: {error}"
        ) from error
    stdout_lines = tuple(
        line.strip() for line in completed.stdout.splitlines() if line.strip()
    )
    diagnostic_lines = tuple(
        line.strip()
        for line in f"{completed.stdout}\n{completed.stderr}".splitlines()
        if line.strip()
    )
    if completed.returncode != 0:
        detail = (
            diagnostic_lines[0]
            if len(diagnostic_lines) > 0
            else f"command exited {completed.returncode}"
        )
        raise ToolVersionResolutionError(
            f"{spec.title} version resolution failed: {detail}"
        )
    if len(stdout_lines) == 0:
        raise ToolVersionResolutionError(
            f"{spec.title} version command completed without reporting a version."
        )
    return ToolVersionResult(spec=spec, version=stdout_lines[0])


def resolve_tool_versions(
    specs: tuple[ToolVersionSpec, ...],
    subprocess_environment: dict[str, str],
) -> tuple[ToolVersionResult, ...]:
    with ThreadPoolExecutor(max_workers=len(specs)) as executor:
        futures = tuple(
            executor.submit(
                _resolve_tool_version,
                spec=spec,
                subprocess_environment=subprocess_environment,
            )
            for spec in specs
        )
        return tuple(future.result() for future in futures)


def build_tool_versions_panel(
    results: tuple[ToolVersionResult, ...],
) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("CLI", style="bold cyan")
    table.add_column("Resolved version", overflow="fold")
    for result in results:
        table.add_row(result.spec.title, Text(result.version))
    return Panel(
        table,
        title="CLI Versions (--latest)",
        border_style="cyan",
    )
