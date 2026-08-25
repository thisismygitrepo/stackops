import re
from pathlib import Path
from typing import Final, Literal

from rich.table import Table

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.constants import DOCTOR_ESTIMATED_CHARACTERS_PER_TOKEN
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorReport, DoctorResource, DoctorResourceState


type ContextDefinitionSource = Literal[
    "MCP / tool config", "Plugins / extensions", "Skill catalog", "AGENTS / instructions", "Other configuration"
]

_CONTEXT_DEFINITION_SOURCES: Final[tuple[ContextDefinitionSource, ...]] = (
    "MCP / tool config",
    "Plugins / extensions",
    "Skill catalog",
    "AGENTS / instructions",
    "Other configuration",
)
_CONTEXT_RESOURCE_STATES: Final[tuple[DoctorResourceState, ...]] = ("active", "available", "configured")


def _definition_source(*, resource: DoctorResource) -> ContextDefinitionSource:
    if resource.is_mcp:
        return "MCP / tool config"
    match resource.kind:
        case "plugin":
            return "Plugins / extensions"
        case "skill":
            return "Skill catalog"
        case "instructions":
            return "AGENTS / instructions"
        case "configuration":
            return "Other configuration"


def _definition_paths(*, report: DoctorReport) -> dict[ContextDefinitionSource, set[Path]]:
    paths_by_source: dict[ContextDefinitionSource, set[Path]] = {
        source: set() for source in _CONTEXT_DEFINITION_SOURCES
    }
    seen_paths: set[Path] = set()
    for resource in report.resources:
        path = resource.path.resolve(strict=False)
        is_inactive_plugin = resource.kind == "plugin" and resource.state == "available"
        if resource.state not in _CONTEXT_RESOURCE_STATES or is_inactive_plugin or not path.is_file() or path in seen_paths:
            continue
        seen_paths.add(path)
        paths_by_source[_definition_source(resource=resource)].add(path)
    return paths_by_source


def _skill_catalog_character_count(*, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    frontmatter_match = re.match(r"^---\s*\n(?P<body>.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
    if frontmatter_match is None:
        return len(text)
    return len(frontmatter_match.group("body")) + len(str(path))


def context_estimate_table(*, report: DoctorReport) -> Table:
    table = Table(
        title="Estimated context definition overhead",
        caption=(
            f"≈{DOCTOR_ESTIMATED_CHARACTERS_PER_TOKEN} characters/token · skill catalog metadata only · config/plugin files are proxies · "
            "runtime tool schemas are unavailable · cumulative % is the share of this estimate"
        ),
        caption_style="dim",
        header_style="bold cyan",
        show_lines=False,
    )
    table.add_column("Source", style="bold", overflow="fold")
    table.add_column("Files", justify="right")
    table.add_column("Characters", justify="right")
    table.add_column("Est. tokens", justify="right")
    table.add_column("Cumulative", justify="right")
    table.add_column("Cum. %", justify="right")

    estimates: list[tuple[ContextDefinitionSource, int, int, int]] = []
    paths_by_source = _definition_paths(report=report)
    for source in _CONTEXT_DEFINITION_SOURCES:
        paths = paths_by_source[source]
        if len(paths) == 0:
            continue
        character_count = (
            sum(_skill_catalog_character_count(path=path) for path in paths)
            if source == "Skill catalog"
            else sum(len(path.read_text(encoding="utf-8")) for path in paths)
        )
        estimated_tokens = (character_count + DOCTOR_ESTIMATED_CHARACTERS_PER_TOKEN - 1) // DOCTOR_ESTIMATED_CHARACTERS_PER_TOKEN
        estimates.append((source, len(paths), character_count, estimated_tokens))
    estimates.sort(key=lambda estimate: (-estimate[3], _CONTEXT_DEFINITION_SOURCES.index(estimate[0])))

    total_files = sum(file_count for _, file_count, _, _ in estimates)
    total_characters = sum(character_count for _, _, character_count, _ in estimates)
    total_tokens = sum(estimated_tokens for _, _, _, estimated_tokens in estimates)
    cumulative_tokens = 0
    for source, file_count, character_count, estimated_tokens in estimates:
        cumulative_tokens += estimated_tokens
        cumulative_percentage = cumulative_tokens / total_tokens * 100.0 if total_tokens > 0 else 0.0
        table.add_row(
            source,
            f"{file_count:,}",
            f"{character_count:,}",
            f"{estimated_tokens:,}",
            f"{cumulative_tokens:,}",
            f"{cumulative_percentage:.1f}%",
        )
    if len(estimates) > 0:
        table.add_section()
    table.add_row(
        "Total",
        f"{total_files:,}",
        f"{total_characters:,}",
        f"{total_tokens:,}",
        f"{total_tokens:,}",
        "100.0%" if total_tokens > 0 else "0.0%",
        style="bold",
    )
    return table
