from pathlib import Path
from subprocess import CompletedProcess
from typing import Callable


def session_sort_key(
    raw_line: str,
    natural_sort_key_fn: Callable[[str], list[int | str]],
    strip_ansi_codes_fn: Callable[[str], str],
) -> tuple[bool, list[int | str]]:
    is_exited = "EXITED" in raw_line
    clean = strip_ansi_codes_fn(raw_line)
    name = clean.split(" [Created")[0].strip()
    return (is_exited, natural_sort_key_fn(name))


def session_name(raw_line: str, strip_ansi_codes_fn: Callable[[str], str]) -> str:
    return strip_ansi_codes_fn(raw_line).split(" [Created")[0].strip()


def session_is_exited(raw_line: str, strip_ansi_codes_fn: Callable[[str], str]) -> bool:
    return "EXITED" in strip_ansi_codes_fn(raw_line)


def session_is_current(raw_line: str, strip_ansi_codes_fn: Callable[[str], str]) -> bool:
    return "(current)" in strip_ansi_codes_fn(raw_line).casefold()


def build_preview(
    raw_line: str,
    run_command_fn: Callable[..., CompletedProcess[str]],
    strip_ansi_codes_fn: Callable[[str], str],
    summarize_layout_fn: Callable[[str], str | None],
    find_latest_session_file_fn: Callable[[str], Path | None],
    read_session_metadata_fn,
    build_metadata_summary_fn: Callable[[list[dict[str, object]], list[dict[str, object]]], str | None],
    get_live_tab_names_fn: Callable[[str], list[str]],
) -> str:
    clean = strip_ansi_codes_fn(raw_line).strip()
    current_session_name = session_name(clean, strip_ansi_codes_fn)
    state = "exited (attach to resurrect)" if session_is_exited(clean, strip_ansi_codes_fn) else "active"
    lines = ["backend: zellij", f"session: {current_session_name}", f"state: {state}"]

    layout_result = run_command_fn(["zellij", "--session", current_session_name, "action", "dump-layout"])
    if layout_result.returncode == 0 and layout_result.stdout.strip():
        summary = summarize_layout_fn(layout_result.stdout)
        lines.append("preview: live layout")
        lines.append("")
        lines.append(summary or layout_result.stdout.strip())
        return "\n".join(lines)

    session_file = find_latest_session_file_fn(current_session_name)
    if session_file is not None:
        session_text = session_file.read_text(encoding="utf-8")
        if session_file.name == "session-metadata.kdl":
            metadata = read_session_metadata_fn(current_session_name)
            summary = build_metadata_summary_fn(*metadata) if metadata is not None else None
            source_kind = "serialized metadata"
        else:
            summary = summarize_layout_fn(session_text)
            source_kind = "serialized layout"
        lines.append(f"preview: {source_kind}")
        lines.append("")
        lines.append(summary or session_text.strip() or "(empty session preview)")
        return "\n".join(lines)

    tab_names = get_live_tab_names_fn(current_session_name)
    if tab_names:
        lines.append("preview: live tab list")
        lines.append("")
        lines.append(f"tabs: {len(tab_names)}")
        lines.extend(f"- {tab_name}" for tab_name in tab_names)
        return "\n".join(lines)

    error_text = (layout_result.stderr or "No preview data available").strip()
    lines.append("")
    lines.append(error_text)
    return "\n".join(lines)
