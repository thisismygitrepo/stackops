"""
This script Takes away all config files from the computer, place them in one directory
`dotfiles`, and create symlinks to those files from thier original locations.

"""

import io
import platform
import subprocess
from pathlib import Path
from typing import Literal, TypedDict

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from stackops.profile.dotfiles_constants import VALID_OS_VALUES, OsName
from stackops.profile.dotfiles_mapper import (
    LIBRARY_MAPPER_PATH,
    USER_MAPPER_PATH,
    MapperDocument,
    OsField,
    RawMapperEntry,
    compose_mapper_documents,
    load_dotfiles_mapper,
)
from stackops.profile.linking.conflict import ON_CONFLICT_STRICT
from stackops.profile.linking.display import classify_action, print_program_line, render_sync_summary
from stackops.profile.linking.operations import ActionType, OperationRecord, OperationResult, copy_map, symlink_map
from stackops.profile.linking.options import CONFIG_FILE_SOURCE_STRICT, CONFIG_SOURCE_LOOSE, CONFIG_SOURCE_MAP, DIRECTION_STRICT
from stackops.utils.source_of_truth import CONFIG_ROOT, DOTFILES_SSH_CREDS_ROOT, resolve_source_of_truth_path

system = platform.system()  # Linux or Windows
SYSTEM = system.lower()

console = Console()

ON_CONFLICT_UP_COPY_MAP: dict[ON_CONFLICT_STRICT, ON_CONFLICT_STRICT] = {
    "throw-error": "throw-error",
    "overwrite-self-managed": "overwrite-default-path",
    "backup-self-managed": "backup-default-path",
    "overwrite-default-path": "overwrite-self-managed",
    "backup-default-path": "backup-self-managed",
}


def normalize_os_name(value: str) -> OsName:
    token = value.strip().lower()
    match token:
        case "darwin":
            return "darwin"
        case "linux":
            return "linux"
        case "windows":
            return "windows"
        case _:
            expected_values = ", ".join(sorted(VALID_OS_VALUES))
            raise ValueError(f"Unsupported operating system: {value!r}. Expected one of: {expected_values}.")


def _parse_os_field(os_field: OsField) -> set[OsName]:
    return set(os_field)


def _resolve_self_managed_path(path_value: str) -> Path:
    return resolve_source_of_truth_path(path_value)


class ConfigMapper(TypedDict):
    file_name: str
    config_file_default_path: str
    config_file_self_managed_path: str
    contents: bool | None
    copy: bool | None
    os: OsField


def _load_mapper_file(source_key: CONFIG_FILE_SOURCE_STRICT) -> MapperDocument:
    match source_key:
        case "user":
            mapper_path = USER_MAPPER_PATH
        case "library":
            mapper_path = LIBRARY_MAPPER_PATH
    if not mapper_path.exists():
        if source_key == "user":
            raise FileNotFoundError(
                f"User dotfiles mapper does not exist: {mapper_path}\n\n"
                "Collect well-known personal files found on this machine:\n"
                "  devops config dotfiles collect\n"
                "Create a real mapping interactively:\n"
                "  devops config setup dotfiles\n"
                "Or install the example and schema for manual editing:\n"
                "  devops config export-example dotfiles --default-path"
            )
        raise FileNotFoundError(f"Packaged dotfiles mapper does not exist: {mapper_path}")
    if not mapper_path.is_file():
        raise IsADirectoryError(f"Dotfiles mapper path is not a file: {mapper_path}")
    try:
        mapper_data: MapperDocument = load_dotfiles_mapper(mapper_path)
    except (TypeError, ValueError, yaml.YAMLError) as exc:
        if source_key == "user":
            raise ValueError(
                f"User dotfiles mapper is invalid: {mapper_path}\n{exc}\n\n"
                "Open it for correction:\n"
                "  devops config edit dotfiles\n"
                "Create a separate example and schema for reference:\n"
                "  devops config export-example dotfiles"
            ) from exc
        raise ValueError(f"Packaged dotfiles mapper is invalid: {mapper_path}\n{exc}") from exc
    return mapper_data


def _read_mapper_document(source: CONFIG_SOURCE_LOOSE) -> MapperDocument:
    source_key = CONFIG_SOURCE_MAP[source]
    match source_key:
        case "user":
            return _load_mapper_file("user")
        case "library" | "all":
            user_mapper = _load_mapper_file("user") if USER_MAPPER_PATH.exists() else {}
            return compose_mapper_documents(library_mapper=_load_mapper_file("library"), user_mapper=user_mapper, source=source_key)


def read_mapper(source: CONFIG_SOURCE_LOOSE) -> dict[str, list[ConfigMapper]]:
    mapper_data = _read_mapper_document(source=source)
    programs: dict[str, list[ConfigMapper]] = {}
    normalized_system = normalize_os_name(SYSTEM)
    for program_key, program_map in mapper_data.items():
        for file_name, file_base in program_map.items():
            os_values = _parse_os_field(file_base["os"])
            if normalized_system not in os_values:
                continue
            programs.setdefault(program_key, []).append(to_config_mapper(file_name=file_name, entry=file_base))
    return programs


def to_config_mapper(file_name: str, entry: RawMapperEntry) -> ConfigMapper:
    return {
        "file_name": file_name,
        "config_file_default_path": entry["original"],
        "config_file_self_managed_path": entry["self_managed"],
        "contents": entry.get("contents"),
        "copy": entry.get("copy"),
        "os": entry["os"],
    }


def _resolve_mapper_paths(a_mapper: ConfigMapper) -> tuple[Path, Path]:
    config_file_default_path = Path(a_mapper["config_file_default_path"]).expanduser().absolute()
    config_file_self_managed_path = _resolve_self_managed_path(a_mapper["config_file_self_managed_path"])
    return config_file_default_path, config_file_self_managed_path


def _get_source_label(direction: DIRECTION_STRICT) -> Literal["default", "self-managed"]:
    if direction == "up":
        return "default"
    return "self-managed"


def _iter_operation_paths(
    config_file_default_path: Path,
    config_file_self_managed_path: Path,
    contents: bool,
    direction: DIRECTION_STRICT,
) -> list[tuple[Path, Path]]:
    source_root = config_file_default_path if direction == "up" else config_file_self_managed_path
    source_label = _get_source_label(direction)
    if not source_root.exists():
        raise FileNotFoundError(f"{direction} sync requires existing {source_label} path: {source_root}")
    if not contents:
        return [(config_file_default_path, config_file_self_managed_path)]
    if not source_root.is_dir():
        raise NotADirectoryError(f"{direction} sync expects a directory for contents mapper: {source_root}")
    source_children = sorted(source_root.glob("*"), key=lambda path: path.name)
    return [
        (
            config_file_default_path.joinpath(source_child.name),
            config_file_self_managed_path.joinpath(source_child.name),
        )
        for source_child in source_children
    ]


def _run_directional_operation(
    config_file_default_path: Path,
    config_file_self_managed_path: Path,
    on_conflict: ON_CONFLICT_STRICT,
    method: Literal["symlink", "copy"],
    direction: DIRECTION_STRICT,
) -> OperationResult:
    if method == "copy" and direction == "up":
        return copy_map(
            config_file_default_path=config_file_self_managed_path,
            config_file_self_managed_path=config_file_default_path,
            on_conflict=ON_CONFLICT_UP_COPY_MAP[on_conflict],
        )
    if method == "copy":
        return copy_map(
            config_file_default_path=config_file_default_path,
            config_file_self_managed_path=config_file_self_managed_path,
            on_conflict=on_conflict,
        )
    return symlink_map(
        config_file_default_path=config_file_default_path,
        config_file_self_managed_path=config_file_self_managed_path,
        on_conflict=on_conflict,
    )


def _append_operation_record(
    operation_records: list[OperationRecord],
    *,
    program_name: str,
    file_key: str,
    config_file_default_path: Path,
    config_file_self_managed_path: Path,
    operation: str,
    action: ActionType,
    details: str,
    status: str,
) -> None:
    operation_records.append(
        {
            "program": program_name,
            "file_key": file_key,
            "defaultPath": str(config_file_default_path),
            "selfManaged": str(config_file_self_managed_path),
            "operation": operation,
            "action": action,
            "details": details,
            "status": status,
        }
    )


def apply_mapper(
    mapper_data: dict[str, list[ConfigMapper]],
    on_conflict: ON_CONFLICT_STRICT,
    method: Literal["symlink", "copy"],
    direction: DIRECTION_STRICT,
) -> list[OperationRecord]:
    operation_records: list[OperationRecord] = []
    import os
    if os.name == "nt":
        import ctypes
        try:
            windll = getattr(ctypes, "windll", None)
            is_admin = bool(windll.shell32.IsUserAnAdmin()) if windll is not None else False
        except Exception:
            is_admin = False
        total_length = sum(len(item) for item in mapper_data.values())
        if not is_admin and method == "symlink" and total_length > 5:
            warning_body = "\n".join([
                "[bold yellow]Administrator privileges required[/]",
                "Run the terminal as admin and try again to avoid repeated elevation prompts.",
            ])
            console.print(
                Panel.fit(
                    warning_body,
                    title="⚠️ Permission Needed",
                    border_style="yellow",
                    padding=(1, 2),
                )
            )
            raise RuntimeError("Run terminal as admin and try again, otherwise, there will be too many popups for admin requests and no chance to terminate the program.")
    name_width = max((len(program_name) for program_name in mapper_data), default=0) + 2
    console.print()
    console.rule(Text(f"""🔗 dotfiles sync {direction} · {method}""", style="bold"), align="left", style="blue")
    for program_name, program_files in mapper_data.items():
        program_start = len(operation_records)
        for a_mapper in program_files:
            config_file_default_path, config_file_self_managed_path = _resolve_mapper_paths(a_mapper)
            use_copy = method == "copy" or a_mapper.get("copy", False)
            resolved_method: Literal["symlink", "copy"] = "copy" if use_copy else "symlink"
            operation_type = f"{direction}_{resolved_method}"
            if a_mapper.get("contents"):
                operation_type = f"{operation_type}_contents"
            try:
                operation_paths = _iter_operation_paths(
                    config_file_default_path=config_file_default_path,
                    config_file_self_managed_path=config_file_self_managed_path,
                    contents=bool(a_mapper.get("contents")),
                    direction=direction,
                )
            except Exception as ex:
                _append_operation_record(
                    operation_records,
                    program_name=program_name,
                    file_key=a_mapper["file_name"],
                    config_file_default_path=config_file_default_path,
                    config_file_self_managed_path=config_file_self_managed_path,
                    operation=operation_type,
                    action="error",
                    details=f"Failed to prepare {operation_type}: {str(ex)}",
                    status=f"error: {str(ex)}",
                )
                continue
            for config_file_default_path_item, config_file_self_managed_path_item in operation_paths:
                try:
                    result = _run_directional_operation(
                        config_file_default_path=config_file_default_path_item,
                        config_file_self_managed_path=config_file_self_managed_path_item,
                        on_conflict=on_conflict,
                        method=resolved_method,
                        direction=direction,
                    )
                    _append_operation_record(
                        operation_records,
                        program_name=program_name,
                        file_key=a_mapper["file_name"],
                        config_file_default_path=config_file_default_path_item,
                        config_file_self_managed_path=config_file_self_managed_path_item,
                        operation=operation_type,
                        action=result["action"],
                        details=result["details"],
                        status=f"""error: {result["details"]}""" if classify_action(action=result["action"]) == "failed" else "success",
                    )
                except ValueError as ex:
                    if "resolve to the same location" in str(ex):
                        _append_operation_record(
                            operation_records,
                            program_name=program_name,
                            file_key=a_mapper["file_name"],
                            config_file_default_path=config_file_default_path_item,
                            config_file_self_managed_path=config_file_self_managed_path_item,
                            operation=operation_type,
                            action="already_linked",
                            details="defaultPath and selfManaged resolve to same location - already correctly configured",
                            status="success",
                        )
                    else:
                        raise
                except Exception as ex:
                    _append_operation_record(
                        operation_records,
                        program_name=program_name,
                        file_key=a_mapper["file_name"],
                        config_file_default_path=config_file_default_path_item,
                        config_file_self_managed_path=config_file_self_managed_path_item,
                        operation=operation_type,
                        action="error",
                        details=f"Failed to create {operation_type}: {str(ex)}",
                        status=f"error: {str(ex)}",
                    )

        if program_name == "ssh" and system == "Linux":
            try:
                for permission_command in (
                    "chmod 700 $HOME/.ssh/",
                    f"chmod 700 {DOTFILES_SSH_CREDS_ROOT}",
                    f"chmod 600 {DOTFILES_SSH_CREDS_ROOT}/*",
                    "chmod 600 $HOME/.ssh/*",
                ):
                    subprocess.run(permission_command, shell=True, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as ex:
                _append_operation_record(
                    operation_records,
                    program_name=program_name,
                    file_key="permissions",
                    config_file_default_path=Path.home().joinpath(".ssh"),
                    config_file_self_managed_path=Path(DOTFILES_SSH_CREDS_ROOT),
                    operation="chmod",
                    action="error",
                    details=f"Failed to set SSH permissions: {str(ex.stderr).strip()}",
                    status=f"error: {str(ex)}",
                )
        print_program_line(console=console, program_name=program_name, records=operation_records[program_start:], name_width=name_width)

    if len(operation_records) > 0:
        import csv
        from datetime import datetime

        csv_dir = Path(CONFIG_ROOT).joinpath("symlink_operations")
        csv_dir.mkdir(parents=True, exist_ok=True)
        csv_path = csv_dir.joinpath(f"""symlink_operations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv""")
        fieldnames = ["program", "file_key", "defaultPath", "selfManaged", "operation", "action", "details", "status"]
        csv_buffer = io.StringIO(newline="")
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(operation_records)
        csv_path.write_text(csv_buffer.getvalue(), encoding="utf-8")
        render_sync_summary(console=console, direction=direction, program_count=len(mapper_data), records=operation_records, csv_path=csv_path)
    return operation_records


if __name__ == "__main__":
    pass
