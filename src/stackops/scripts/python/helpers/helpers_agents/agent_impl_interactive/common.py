import os
import shlex
import shutil
import subprocess
from pathlib import Path

from stackops.utils.accessories import get_repo_root, randstr
from stackops.utils.options import choose_from_options


NONE_LABEL = "<leave empty>"


def order_current_first[T: str](options: tuple[T, ...] | list[T], current: T | None) -> list[T]:
    ordered = list(options)
    if current is not None and current in ordered:
        ordered.remove(current)
        ordered.insert(0, current)
    return ordered


def choose_required_option(*, options: tuple[str, ...] | list[str], msg: str, header: str) -> str:
    selection = choose_from_options(options=list(options), msg=msg, multi=False, custom_input=False, header=header, tv=True)
    if selection is None:
        raise ValueError(f"Selection cancelled for {header.lower()}")
    return selection


def choose_optional_option(*, options: tuple[str, ...] | list[str], current: str | None, msg: str, header: str) -> str | None:
    labels = list(order_current_first(options=options, current=current))
    insert_at = 0 if current is None else 1
    labels.insert(insert_at, NONE_LABEL)
    selection = choose_required_option(options=labels, msg=msg, header=header)
    if selection == NONE_LABEL:
        return None
    return selection


def prompt_text(*, label: str, current: str | None, required: bool, hint: str) -> str | None:
    suffix = f" [{current}]" if current else ""
    while True:
        raw = input(f"{label}{suffix}{hint}: ").strip()
        if raw != "":
            return raw
        if current is not None:
            return current
        if not required:
            return None
        print(f"{label} is required.")


def prompt_bool(*, label: str, current: bool) -> bool:
    current_label = "true" if current else "false"
    chosen = choose_required_option(
        options=order_current_first(options=["true", "false"], current=current_label),
        msg=f"Choose {label}",
        header=label.replace("_", " ").title(),
    )
    return chosen == "true"


def prompt_optional_text_value(*, label: str, current: str | None) -> str | None:
    shown_current = NONE_LABEL if current is None else current
    raw = input(f"{label} [{shown_current}] (blank keeps current, type {NONE_LABEL} to clear): ").strip()
    if raw == "":
        return current
    if raw == NONE_LABEL:
        return None
    return raw


def prompt_positive_int(*, label: str, current: int) -> int:
    starting_value = current if current > 0 else 3
    while True:
        raw = input(f"{label} [{starting_value}]: ").strip()
        chosen = raw if raw != "" else str(starting_value)
        try:
            value = int(chosen, 10)
        except ValueError:
            print(f"{label} must be a positive integer.")
            continue
        if value <= 0:
            print(f"{label} must be a positive integer.")
            continue
        return value


def _discover_editor_command() -> list[str] | None:
    configured_editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if configured_editor:
        return shlex.split(configured_editor)
    for candidate in ("nano", "vim", "vi"):
        resolved = shutil.which(candidate)
        if resolved is not None:
            return [resolved]
    return None


def _editor_scratch_path(*, label: str, suffix: str) -> Path:
    repo_root = get_repo_root(Path.cwd())
    base_dir = Path("/tmp/stackops_agent_impl_interactive") if repo_root is None else repo_root / ".ai" / "tmp_scripts" / "agent_impl_interactive"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{label.replace(' ', '_')}_{randstr(length=6, lower=True, upper=False, digits=False, punctuation=False)}{suffix}"


def _edit_text(*, label: str, current: str | None) -> str | None:
    editor_command = _discover_editor_command()
    if editor_command is None:
        print(f"Enter {label}. Finish with a line containing only .done")
        lines: list[str] = []
        while True:
            line = input()
            if line == ".done":
                break
            lines.append(line)
        value = "\n".join(lines).strip()
        if value != "":
            return value
        return current
    temp_path = _editor_scratch_path(label=label, suffix=".md")
    temp_path.write_text("" if current is None else current, encoding="utf-8")
    try:
        subprocess.run([*editor_command, str(temp_path)], check=False)
        value = temp_path.read_text(encoding="utf-8").strip()
        if value != "":
            return value
        return current
    finally:
        temp_path.unlink(missing_ok=True)


def prompt_multiline_text(*, label: str, current: str | None, required: bool) -> str | None:
    while True:
        value = _edit_text(label=label, current=current)
        if value is not None and value.strip() != "":
            return value
        if not required:
            return None
        print(f"{label} is required.")


def prompt_existing_path(*, label: str, current: str | None, must_be_file: bool) -> str:
    suffix = f" [{current}]" if current else ""
    while True:
        raw = input(f"{label}{suffix}: ").strip()
        path_raw = raw if raw != "" else current
        if path_raw is None:
            print(f"{label} is required.")
            continue
        path_obj = Path(path_raw).expanduser().resolve()
        if not path_obj.exists():
            print(f"{label} does not exist: {path_obj}")
            continue
        if must_be_file and not path_obj.is_file():
            print(f"{label} must be a file: {path_obj}")
            continue
        return str(path_obj)


def _decode_separator(raw_separator: str) -> str:
    try:
        return bytes(raw_separator, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        return raw_separator


def _strip_editor_trailing_newline(value: str) -> str:
    return value.removesuffix("\n").removesuffix("\r")


def prompt_separator(*, current: str) -> str:
    displayed = current.encode("unicode_escape").decode("ascii")
    editor_command = _discover_editor_command()
    if editor_command is None:
        raw = input(f"separator [{displayed}] (escape sequences like \\\\n are supported): ")
        if raw == "":
            return current
        return _decode_separator(raw)
    temp_path = _editor_scratch_path(label="separator", suffix=".txt")
    temp_path.write_text(displayed, encoding="utf-8")
    try:
        subprocess.run([*editor_command, str(temp_path)], check=False)
        raw = _strip_editor_trailing_newline(temp_path.read_text(encoding="utf-8"))
        if raw == "":
            return current
        return _decode_separator(raw)
    finally:
        temp_path.unlink(missing_ok=True)


def separator_is_applicable_for_context_path(context_path: Path) -> bool:
    if context_path.is_file():
        return True
    if not context_path.is_dir():
        return True
    text_files = [item for item in context_path.rglob("*") if item.is_file() and item.suffix.lower() in {".md", ".txt"}]
    return len(text_files) <= 1
