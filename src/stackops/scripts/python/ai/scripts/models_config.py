import atexit
import json
import os
import re
import tempfile
import tomllib
from pathlib import Path
from typing import Final

from stackops.scripts.python.ai.scripts.models_core import REPORTS_DIR, ToolSpec


TYPE_CHECK_EXCLUDES_ENV_VAR: Final[str] = "STACKOPS_TYPE_CHECK_EXCLUDES"
TYPE_CHECK_LATEST_ENV_VAR: Final[str] = "STACKOPS_TYPE_CHECK_LATEST"
MYPY_EXCLUDE_PATTERN: Final[str] = r"(^|/|\\)gromit-mpx($|/|\\)"
PYRIGHT_CONFIG_PATH: Final[Path] = Path("pyrightconfig.json")
PYPROJECT_PATH: Final[Path] = Path("pyproject.toml")
PYRIGHT_CONFIG_OVERRIDE_PATH: Final[Path] = Path(".pyright.type-check.override.json")


def _remove_generated_file(path: Path) -> None:
    path.unlink(missing_ok=True)


def _create_pyright_config_override_path() -> Path:
    file_descriptor, raw_path = tempfile.mkstemp(
        prefix=f"{PYRIGHT_CONFIG_OVERRIDE_PATH.stem}.",
        suffix=PYRIGHT_CONFIG_OVERRIDE_PATH.suffix,
        dir=Path.cwd(),
    )
    os.close(file_descriptor)
    return Path(raw_path)


def load_type_check_excluded_directories() -> tuple[str, ...]:
    raw_value = os.environ.get(TYPE_CHECK_EXCLUDES_ENV_VAR)
    if raw_value is None or raw_value == "":
        return ()
    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid {TYPE_CHECK_EXCLUDES_ENV_VAR} value. Expected a JSON array of strings."
        ) from error
    if not isinstance(payload, list):
        raise ValueError(
            f"Invalid {TYPE_CHECK_EXCLUDES_ENV_VAR} value. Expected a JSON array of strings."
        )
    excluded_directories: list[str] = []
    seen_directories: set[str] = set()
    for item in payload:
        if not isinstance(item, str) or item == "":
            raise ValueError(
                f"Invalid {TYPE_CHECK_EXCLUDES_ENV_VAR} value. Expected a JSON array of strings."
            )
        if item in seen_directories:
            continue
        seen_directories.add(item)
        excluded_directories.append(item)
    return tuple(excluded_directories)


def load_latest_type_check_tools() -> bool:
    raw_value = os.environ.get(TYPE_CHECK_LATEST_ENV_VAR, "0")
    if raw_value == "1":
        return True
    if raw_value == "0":
        return False
    raise ValueError(f"Invalid {TYPE_CHECK_LATEST_ENV_VAR} value. Expected '1' or '0'.")


def _merge_distinct_strings(*groups: tuple[str, ...]) -> tuple[str, ...]:
    merged_values: list[str] = []
    seen_values: set[str] = set()
    for group in groups:
        for value in group:
            if value in seen_values:
                continue
            seen_values.add(value)
            merged_values.append(value)
    return tuple(merged_values)


def _build_directory_regex(relative_directory: str) -> str:
    escaped_directory = re.escape(relative_directory).replace("/", r"(/|\\)")
    return rf"(^|/|\\){escaped_directory}($|/|\\)"


def _build_combined_regex(patterns: tuple[str, ...]) -> str:
    return "|".join(f"(?:{pattern})" for pattern in patterns)


def _append_repeated_option(
    command: list[str], option: str, values: tuple[str, ...]
) -> None:
    for value in values:
        command.extend((option, value))


def build_uv_tool_command(package: str, latest: bool) -> list[str]:
    if latest:
        command = ["uv", "run", "--isolated", "--upgrade-package", package]
    else:
        command = ["uv", "run", "--frozen"]
    command.extend(("--with", package))
    return command


def _parse_jsonc_object(raw_text: str) -> dict[str, object]:
    text_without_comments = "\n".join(
        line for line in raw_text.splitlines() if not line.lstrip().startswith("//")
    )
    normalized_text = re.sub(r",(\s*[}\]])", r"\1", text_without_comments)
    payload = json.loads(normalized_text)
    if not isinstance(payload, dict):
        raise ValueError("Pyright configuration must be a JSON object.")
    return payload


def _load_pyright_base_config() -> tuple[dict[str, object], bool]:
    if PYRIGHT_CONFIG_PATH.exists():
        return (
            _parse_jsonc_object(PYRIGHT_CONFIG_PATH.read_text(encoding="utf-8")),
            True,
        )
    if PYPROJECT_PATH.exists():
        pyproject_payload = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
        tool_section = pyproject_payload.get("tool")
        if isinstance(tool_section, dict):
            pyright_section = tool_section.get("pyright")
            if isinstance(pyright_section, dict):
                return dict(pyright_section), False
    return {}, False


def _extract_pyright_excludes(config: dict[str, object]) -> tuple[str, ...]:
    raw_excludes = config.get("exclude")
    if raw_excludes is None:
        return ()
    if not isinstance(raw_excludes, list):
        raise ValueError("Pyright config 'exclude' must be a list of strings.")
    excludes: list[str] = []
    for item in raw_excludes:
        if not isinstance(item, str):
            raise ValueError("Pyright config 'exclude' must be a list of strings.")
        excludes.append(item)
    return tuple(excludes)


def _ensure_pyright_config_override(excluded_directories: tuple[str, ...]) -> Path:
    base_config, has_pyright_config = _load_pyright_base_config()
    merged_excludes = _merge_distinct_strings(
        _extract_pyright_excludes(base_config), excluded_directories
    )
    override_path = _create_pyright_config_override_path()
    override_config: dict[str, object]
    if has_pyright_config:
        override_config = {
            "extends": f"./{PYRIGHT_CONFIG_PATH.as_posix()}",
            "exclude": list(merged_excludes),
        }
    else:
        override_config = dict(base_config)
        override_config["exclude"] = list(merged_excludes)
    override_path.write_text(json.dumps(override_config, indent=2) + "\n", encoding="utf-8")
    atexit.register(_remove_generated_file, override_path)
    return override_path


def build_cleanup_commands(
    excluded_directories: tuple[str, ...],
    latest: bool,
) -> tuple[tuple[str, ...], ...]:
    excluded_patterns = tuple(
        _build_directory_regex(directory) for directory in excluded_directories
    )
    cleanpy_command = build_uv_tool_command(package="cleanpy", latest=latest)
    cleanpy_command.extend(("-m", "cleanpy"))
    _append_repeated_option(
        command=cleanpy_command, option="--exclude", values=excluded_patterns
    )
    cleanpy_command.append(".")
    ruff_fix_command = build_uv_tool_command(package="ruff", latest=latest)
    ruff_fix_command.extend(("ruff", "check", "--fix"))
    if len(excluded_directories) > 0:
        ruff_fix_command.append("--force-exclude")
        _append_repeated_option(
            command=ruff_fix_command,
            option="--extend-exclude",
            values=excluded_directories,
        )
    ruff_fix_command.append(".")
    return (
        tuple(cleanpy_command),
        (*build_uv_tool_command(package="ruff", latest=latest), "-m", "ruff", "clean"),
        tuple(ruff_fix_command),
    )


def build_checker_specs(
    excluded_directories: tuple[str, ...],
    latest: bool,
) -> tuple[ToolSpec, ...]:
    excluded_patterns = tuple(
        _build_directory_regex(directory) for directory in excluded_directories
    )
    mypy_excludes = _merge_distinct_strings((MYPY_EXCLUDE_PATTERN,), excluded_patterns)
    pyright_command = build_uv_tool_command(package="pyright", latest=latest)
    pyright_command.extend(("pyright", "--outputjson", "--threads", "10"))
    if len(excluded_directories) > 0:
        pyright_command.extend(
            ("--project", str(_ensure_pyright_config_override(excluded_directories)))
        )
    pyright_command.append(".")
    mypy_command = build_uv_tool_command(package="mypy", latest=latest)
    mypy_command.extend(("mypy", "-O", "json"))
    _append_repeated_option(command=mypy_command, option="--exclude", values=mypy_excludes)
    mypy_command.append(".")
    pylint_command = build_uv_tool_command(package="pylint", latest=latest)
    pylint_command.extend(
        (
            "pylint",
            "--recursive=y",
            "--jobs=5",
            "--ignore=.venv",
            "--output-format=json2",
            "--score=n",
            "--reports=n",
        )
    )
    if len(excluded_patterns) > 0:
        pylint_command.extend(("--ignore-paths", _build_combined_regex(excluded_patterns)))
    pylint_command.append(".")
    pyrefly_command = build_uv_tool_command(package="pyrefly", latest=latest)
    pyrefly_command.extend(
        ("pyrefly", "check", "--summary=none", "--output-format", "json")
    )
    _append_repeated_option(
        command=pyrefly_command,
        option="--project-excludes",
        values=excluded_directories,
    )
    pyrefly_command.append(".")
    ty_command = build_uv_tool_command(package="ty", latest=latest)
    ty_command.extend(("ty", "check", "--no-progress", "--output-format", "gitlab"))
    if len(excluded_directories) > 0:
        ty_command.append("--force-exclude")
        _append_repeated_option(
            command=ty_command, option="--exclude", values=excluded_directories
        )
    ty_command.append(".")
    ruff_command = build_uv_tool_command(package="ruff", latest=latest)
    ruff_command.extend(("ruff", "check", "--output-format", "json"))
    if len(excluded_directories) > 0:
        ruff_command.append("--force-exclude")
        _append_repeated_option(
            command=ruff_command,
            option="--extend-exclude",
            values=excluded_directories,
        )
    ruff_command.append(".")
    return (
        ToolSpec(
            slug="pyright",
            title="Pyright Type Checker",
            report_path=REPORTS_DIR / "issues_pyright.md",
            command=tuple(pyright_command),
            output_format="json",
        ),
        ToolSpec(
            slug="mypy",
            title="MyPy Type Checker",
            report_path=REPORTS_DIR / "issues_mypy.md",
            command=tuple(mypy_command),
            output_format="json",
        ),
        ToolSpec(
            slug="pylint",
            title="Pylint Code Analysis",
            report_path=REPORTS_DIR / "issues_pylint.md",
            command=tuple(pylint_command),
            output_format="json",
        ),
        ToolSpec(
            slug="pyrefly",
            title="Pyrefly Type Checker",
            report_path=REPORTS_DIR / "issues_pyrefly.md",
            command=tuple(pyrefly_command),
            output_format="json",
        ),
        ToolSpec(
            slug="ty",
            title="Ty Type Checker",
            report_path=REPORTS_DIR / "issues_ty.md",
            command=tuple(ty_command),
            output_format="json",
        ),
        ToolSpec(
            slug="ruff",
            title="Ruff Linter",
            report_path=REPORTS_DIR / "issues_ruff.md",
            command=tuple(ruff_command),
            output_format="json",
        ),
    )
