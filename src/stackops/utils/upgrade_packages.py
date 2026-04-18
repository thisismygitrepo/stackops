"""Generate upgrade scripts and clean dependency groups in pyproject.toml."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import subprocess
import tomllib
from typing import Literal, TypedDict, cast


ProjectTable = TypedDict(
    "ProjectTable",
    {
        "dependencies": list[str],
        "optional-dependencies": dict[str, list[str]],
        "version": str,
    },
    total=False,
)
PyprojectTable = TypedDict(
    "PyprojectTable",
    {
        "project": ProjectTable,
        "dependency-groups": dict[str, list[str]],
    },
    total=False,
)
CleanupKind = Literal["dependency-group", "optional-dependency"]
AddCommandScope = Literal["main", "dependency-group", "optional-dependency"]


@dataclass(frozen=True)
class CleanupTarget:
    kind: CleanupKind
    group_name: str
    packages: tuple[str, ...]


def read_pyproject(pyproject_path: Path) -> PyprojectTable:
    return cast(PyprojectTable, tomllib.loads(pyproject_path.read_text(encoding="utf-8")))


def generate_uv_add_commands(pyproject_path: Path, output_path: Path) -> None:
    pyproject_data = read_pyproject(pyproject_path=pyproject_path)
    commands: list[str] = []

    main_dependencies = get_main_dependencies(pyproject_data=pyproject_data)
    if main_dependencies:
        commands.append(build_uv_add_command(packages=main_dependencies, group_name=None, scope="main"))

    for group_name, dependencies in get_optional_dependencies(pyproject_data=pyproject_data).items():
        if dependencies:
            commands.append(
                build_uv_add_command(packages=dependencies, group_name=group_name, scope="optional-dependency")
            )

    for group_name, dependencies in get_dependency_groups(pyproject_data=pyproject_data).items():
        if dependencies:
            commands.append(build_uv_add_command(packages=dependencies, group_name=group_name, scope="dependency-group"))

    script = f"""
#!/bin/bash
set -e
uv cache clean --force
rm -rfd .venv
{"".join(f"{command}\n" for command in commands)}
"""
    output_path.write_text(script.strip() + "\n", encoding="utf-8")
    print(f"Generated {len(commands)} uv add commands in {output_path}")


def clean_dependency_groups(project_root: Path, group_names: Sequence[str]) -> None:
    pyproject_path = project_root / "pyproject.toml"
    pyproject_data = read_pyproject(pyproject_path=pyproject_path)

    cleanup_targets = resolve_cleanup_targets(pyproject_data=pyproject_data, group_names=group_names)
    for cleanup_target in cleanup_targets:
        if not cleanup_target.packages:
            print(f"{cleanup_target.kind} '{cleanup_target.group_name}' is already empty")
            continue
        subprocess.run(build_uv_remove_command(cleanup_target=cleanup_target), cwd=project_root, check=True)
        print(f"Cleaned {cleanup_target.kind} '{cleanup_target.group_name}'")


def resolve_cleanup_targets(pyproject_data: PyprojectTable, group_names: Sequence[str]) -> list[CleanupTarget]:
    optional_dependencies = get_optional_dependencies(pyproject_data=pyproject_data)
    dependency_groups = get_dependency_groups(pyproject_data=pyproject_data)

    cleanup_targets: list[CleanupTarget] = []
    missing_groups: list[str] = []
    seen_group_names: set[str] = set()

    for group_name in group_names:
        if group_name in seen_group_names:
            continue
        seen_group_names.add(group_name)

        matched_group = False

        optional_group_packages = optional_dependencies.get(group_name)
        if optional_group_packages is not None:
            matched_group = True
            cleanup_targets.append(
                CleanupTarget(
                    kind="optional-dependency",
                    group_name=group_name,
                    packages=tuple(extract_package_name(dependency_spec) for dependency_spec in optional_group_packages),
                )
            )

        dependency_group_packages = dependency_groups.get(group_name)
        if dependency_group_packages is not None:
            matched_group = True
            cleanup_targets.append(
                CleanupTarget(
                    kind="dependency-group",
                    group_name=group_name,
                    packages=tuple(extract_package_name(dependency_spec) for dependency_spec in dependency_group_packages),
                )
            )

        if not matched_group:
            missing_groups.append(group_name)

    if missing_groups:
        missing_groups_csv = ", ".join(missing_groups)
        raise ValueError(f"Unknown dependency group or optional dependency extra: {missing_groups_csv}")

    return cleanup_targets


def build_uv_add_command(packages: Sequence[str], group_name: str | None, scope: AddCommandScope) -> str:
    package_names = " ".join(f"'{extract_package_name(dependency_spec)}'" for dependency_spec in packages)
    match scope:
        case "main":
            return f"uv add --no-cache {package_names}"
        case "optional-dependency":
            if group_name is None:
                raise ValueError("group_name is required for optional dependency commands")
            return f"uv add --no-cache --optional {group_name} {package_names}"
        case "dependency-group":
            if group_name is None:
                raise ValueError("group_name is required for dependency group commands")
            if group_name == "dev":
                return f"uv add --no-cache --dev {package_names}"
            return f"uv add --no-cache --group {group_name} {package_names}"


def build_uv_remove_command(cleanup_target: CleanupTarget) -> list[str]:
    match cleanup_target.kind:
        case "optional-dependency":
            return ["uv", "remove", "--optional", cleanup_target.group_name, *cleanup_target.packages, "--no-sync"]
        case "dependency-group":
            if cleanup_target.group_name == "dev":
                return ["uv", "remove", "--dev", *cleanup_target.packages, "--no-sync"]
            return ["uv", "remove", "--group", cleanup_target.group_name, *cleanup_target.packages, "--no-sync"]
        case _:
            raise ValueError(f"Unsupported cleanup target kind: {cleanup_target.kind}")


def get_main_dependencies(pyproject_data: PyprojectTable) -> list[str]:
    project_table = pyproject_data.get("project")
    if project_table is None:
        return []
    return project_table.get("dependencies", [])


def get_optional_dependencies(pyproject_data: PyprojectTable) -> dict[str, list[str]]:
    project_table = pyproject_data.get("project")
    if project_table is None:
        return {}
    return project_table.get("optional-dependencies", {})


def get_dependency_groups(pyproject_data: PyprojectTable) -> dict[str, list[str]]:
    return pyproject_data.get("dependency-groups", {})


def extract_package_name(dependency_spec: str) -> str:
    dependency_spec_without_markers = dependency_spec.split(";", maxsplit=1)[0].strip()
    for operator in [">=", "<=", "==", "!=", ">", "<", "~=", "===", "@"]:
        if operator in dependency_spec_without_markers:
            return dependency_spec_without_markers.split(operator, maxsplit=1)[0].strip()
    return dependency_spec_without_markers


def upgrade_machine_config_version() -> None:
    current_dir = Path.cwd()
    pyproject_file = current_dir / "pyproject.toml"
    pyproject_data = read_pyproject(pyproject_path=pyproject_file)

    project_table = pyproject_data.get("project")
    if project_table is None or "version" not in project_table:
        raise ValueError(f"Missing project.version in {pyproject_file}")

    current_version_str = project_table["version"]
    version_parts = current_version_str.split(".")
    major = int(version_parts[0])
    minor = int(version_parts[1])
    new_minor = minor + 1
    new_version = f"{major}.{new_minor:0{len(version_parts[1])}d}"

    optional_groups: set[str] = set(get_optional_dependencies(pyproject_data=pyproject_data))
    optional_groups.update(get_dependency_groups(pyproject_data=pyproject_data))

    print(f"Upgrading from {current_version_str} to {new_version}")
    print(f"Found optional groups: {', '.join(sorted(optional_groups))}")

    content = pyproject_file.read_text(encoding="utf-8")
    updated_content = content.replace(f'version = "{current_version_str}"', f'version = "{new_version}"')
    pyproject_file.write_text(updated_content, encoding="utf-8")
    print(f"Updated pyproject.toml: {current_version_str} -> {new_version}")

    source_files = list(current_dir.glob("**/*.py")) + list(current_dir.glob("**/*.sh")) + list(current_dir.glob("**/*.ps1"))
    source_files.extend(file_path for file_path in current_dir.glob("**/Dockerfile*") if file_path.is_file())

    files_updated = 0
    for file_path in source_files:
        try:
            file_content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        updated_file_content = file_content.replace(
            f"stackops>={current_version_str}",
            f"stackops>={new_version}",
        )
        for group_name in optional_groups:
            updated_file_content = updated_file_content.replace(
                f"stackops[{group_name}]>={current_version_str}",
                f"stackops[{group_name}]>={new_version}",
            )

        if updated_file_content == file_content:
            continue

        file_path.write_text(updated_file_content, encoding="utf-8")
        files_updated += 1
        print(f"Updated {file_path.relative_to(current_dir)}")

    print(f"Updated {files_updated} files with version constraint")

    from stackops.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(f"cd {current_dir}; uv sync")


if __name__ == "__main__":
    upgrade_machine_config_version()
