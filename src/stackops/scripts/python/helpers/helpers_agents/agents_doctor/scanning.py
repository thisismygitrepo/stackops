import json
import os
import re
import shutil
import subprocess
import tomllib
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Literal, cast

import yaml

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.constants import DOCTOR_VERSION_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import (
    DoctorAgentDefinition,
    DoctorContext,
    DoctorExecutableStatus,
    DoctorOrigin,
    DoctorReport,
    DoctorResource,
    DoctorResourceKind,
    DoctorResourceState,
)
from stackops.utils.accessories import get_repo_root
from stackops.utils.files.read import remove_c_style_comments


type ConfigFormat = Literal["json", "toml", "yaml"]


def _environment_path(*, variable_name: str, fallback: Path) -> Path:
    raw_value = os.environ.get(variable_name)
    if raw_value is None or raw_value.strip() == "":
        return fallback.resolve(strict=False)
    return Path(raw_value).expanduser().resolve(strict=False)


def _omp_home(*, home_directory: Path) -> Path:
    profile = os.environ.get("OMP_PROFILE")
    if profile is not None and profile.strip() not in ("", "default"):
        return home_directory.joinpath(".omp", "profiles", profile.strip(), "agent").resolve(strict=False)
    return _environment_path(variable_name="PI_CODING_AGENT_DIR", fallback=home_directory.joinpath(".omp", "agent"))


def create_doctor_context(*, working_directory: Path) -> DoctorContext:
    resolved_working_directory = working_directory.expanduser().resolve(strict=False)
    detected_repo_root = get_repo_root(resolved_working_directory)
    project_root = (detected_repo_root or resolved_working_directory).resolve(strict=False)
    relative_parts = resolved_working_directory.relative_to(project_root).parts
    ancestor_directories = tuple(
        project_root.joinpath(*relative_parts[:part_count]).resolve(strict=False) for part_count in range(len(relative_parts) + 1)
    )
    home_directory = Path.home().resolve(strict=False)
    return DoctorContext(
        working_directory=resolved_working_directory,
        project_root=project_root,
        ancestor_directories=ancestor_directories,
        home_directory=home_directory,
        xdg_config_directory=_environment_path(variable_name="XDG_CONFIG_HOME", fallback=home_directory / ".config"),
        xdg_data_directory=_environment_path(variable_name="XDG_DATA_HOME", fallback=home_directory / ".local" / "share"),
        codex_home=_environment_path(variable_name="CODEX_HOME", fallback=home_directory / ".codex"),
        pi_home=_environment_path(variable_name="PI_CODING_AGENT_DIR", fallback=home_directory / ".pi" / "agent"),
        omp_home=_omp_home(home_directory=home_directory),
        claude_home=_environment_path(variable_name="CLAUDE_CONFIG_DIR", fallback=home_directory / ".claude"),
    )


def resource_candidate(
    *,
    kind: DoctorResourceKind,
    is_mcp: bool,
    name: str,
    origin: DoctorOrigin,
    path: Path,
    present_state: DoctorResourceState,
    detail: str,
    include_missing: bool,
) -> DoctorResource | None:
    resolved_path = path.expanduser().resolve(strict=False)
    if resolved_path.exists():
        return DoctorResource(kind=kind, is_mcp=is_mcp, name=name, origin=origin, state=present_state, path=resolved_path, detail=detail)
    if include_missing:
        return DoctorResource(kind=kind, is_mcp=is_mcp, name=name, origin=origin, state="missing", path=resolved_path, detail=detail)
    return None


def present_resources(*, candidates: Iterable[DoctorResource | None]) -> tuple[DoctorResource, ...]:
    return tuple(candidate for candidate in candidates if candidate is not None)


def _skill_name(*, skill_path: Path) -> str:
    try:
        text = skill_path.read_text(encoding="utf-8")
    except OSError:
        return skill_path.parent.name
    frontmatter_match = re.match(r"^---\s*\n(?P<body>.*?)\n---\s*(?:\n|$)", text, flags=re.DOTALL)
    if frontmatter_match is None:
        return skill_path.parent.name
    name_match = re.search(r"^name:\s*(?P<name>.+?)\s*$", frontmatter_match.group("body"), flags=re.MULTILINE)
    if name_match is None:
        return skill_path.parent.name
    return name_match.group("name").strip().strip("\"'")


def scan_skill_roots(*, roots: Sequence[tuple[DoctorOrigin, Path, str]], recursive: bool, state: DoctorResourceState) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    seen_paths: set[Path] = set()
    for origin, root, detail in roots:
        if not root.is_dir():
            continue
        paths = root.rglob("SKILL.md") if recursive else root.glob("*/SKILL.md")
        for path in sorted(paths):
            resolved_path = path.resolve(strict=False)
            if resolved_path in seen_paths or "node_modules" in resolved_path.parts:
                continue
            seen_paths.add(resolved_path)
            resources.append(
                DoctorResource(
                    kind="skill",
                    is_mcp=False,
                    name=_skill_name(skill_path=resolved_path),
                    origin=origin,
                    state=state,
                    path=resolved_path,
                    detail=detail,
                )
            )
    return tuple(resources)


def scan_plugin_roots(
    *, roots: Sequence[tuple[DoctorOrigin, Path, str]], patterns: Sequence[str], state: DoctorResourceState
) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    seen_paths: set[Path] = set()
    for origin, root, detail in roots:
        if not root.is_dir():
            continue
        for pattern in patterns:
            for path in sorted(root.glob(pattern)):
                if not path.is_file():
                    continue
                resolved_path = path.resolve(strict=False)
                if resolved_path in seen_paths or "node_modules" in resolved_path.parts:
                    continue
                seen_paths.add(resolved_path)
                name = resolved_path.parent.name if resolved_path.name.startswith("index.") else resolved_path.stem
                resources.append(
                    DoctorResource(kind="plugin", is_mcp=False, name=name, origin=origin, state=state, path=resolved_path, detail=detail)
                )
    return tuple(resources)


def load_config_mapping(*, path: Path, config_format: ConfigFormat) -> dict[str, object] | str:
    try:
        text = path.read_text(encoding="utf-8")
        match config_format:
            case "json":
                value: object = json.loads(remove_c_style_comments(text))
            case "toml":
                value = tomllib.loads(text)
            case "yaml":
                value = cast(object, yaml.safe_load(text))
    except (OSError, ValueError, tomllib.TOMLDecodeError, yaml.YAMLError) as error:
        return str(error)
    if value is None:
        return {}
    if not isinstance(value, dict):
        return "configuration root is not an object"
    return cast(dict[str, object], value)


def _version_status(*, definition: DoctorAgentDefinition) -> DoctorExecutableStatus:
    executable_path = shutil.which(definition.executable)
    if executable_path is None:
        return DoctorExecutableStatus(installed=False, path=None, version=None, error=None)
    resolved_executable_path = Path(executable_path).resolve(strict=False)
    try:
        result = subprocess.run(
            [executable_path, *definition.version_arguments], check=False, capture_output=True, text=True, timeout=DOCTOR_VERSION_TIMEOUT_SECONDS
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return DoctorExecutableStatus(installed=True, path=resolved_executable_path, version=None, error=str(error))
    output_lines = tuple(line.strip() for line in (result.stdout + "\n" + result.stderr).splitlines() if line.strip())
    if result.returncode == 0 and len(output_lines) > 0:
        return DoctorExecutableStatus(installed=True, path=resolved_executable_path, version=output_lines[0], error=None)
    error = output_lines[0] if len(output_lines) > 0 else f"version command exited {result.returncode}"
    return DoctorExecutableStatus(installed=True, path=resolved_executable_path, version=None, error=error)


def build_doctor_report(*, definition: DoctorAgentDefinition, working_directory: Path) -> DoctorReport:
    context = create_doctor_context(working_directory=working_directory)
    resources = definition.collector(context=context)
    return DoctorReport(definition=definition, context=context, executable=_version_status(definition=definition), resources=resources)
