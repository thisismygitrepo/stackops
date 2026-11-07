import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from rich import box
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stackops.scripts.python.ai.scripts.constants import CheckerName, ToolVersionMode
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


def build_tool_upgrade_command(selected_tools: tuple[CheckerName, ...]) -> tuple[str, ...]:
    command = ["uv", "lock"]
    for package in ("cleanpy", *selected_tools):
        command.extend(("--upgrade-package", package))
    return tuple(command)


def build_tool_version_specs(
    tool_versions: ToolVersionMode, selected_tools: tuple[CheckerName, ...]
) -> tuple[ToolVersionSpec, ...]:
    specs = (
        ToolVersionSpec(
            title="Cleanpy",
            command=(
                *build_uv_tool_command(package="cleanpy", tool_versions=tool_versions),
                "-m",
                "cleanpy",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Ruff",
            command=(
                *build_uv_tool_command(package="ruff", tool_versions=tool_versions),
                "ruff",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Pyright",
            command=(
                *build_uv_tool_command(package="pyright", tool_versions=tool_versions),
                "pyright",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="MyPy",
            command=(
                *build_uv_tool_command(package="mypy", tool_versions=tool_versions),
                "mypy",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Pylint",
            command=(
                *build_uv_tool_command(package="pylint", tool_versions=tool_versions),
                "pylint",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Pyrefly",
            command=(
                *build_uv_tool_command(package="pyrefly", tool_versions=tool_versions),
                "pyrefly",
                "--version",
            ),
        ),
        ToolVersionSpec(
            title="Ty",
            command=(
                *build_uv_tool_command(package="ty", tool_versions=tool_versions),
                "ty",
                "--version",
            ),
        ),
    )
    return tuple(
        spec
        for spec in specs
        if spec.title == "Cleanpy" or spec.title.lower() in selected_tools
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
    results: tuple[ToolVersionResult, ...], tool_versions: ToolVersionMode
) -> Panel:
    table = Table(box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("CLI", style="bold cyan")
    table.add_column("Resolved version", overflow="fold")
    for result in results:
        table.add_row(result.spec.title, Text(result.version))
    return Panel(
        table,
        title=f"CLI Versions (--tool-versions {tool_versions})",
        border_style="cyan",
    )
