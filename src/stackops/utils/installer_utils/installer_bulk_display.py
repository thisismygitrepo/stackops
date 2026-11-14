import os
import re
from collections import Counter
from pathlib import Path
from typing import Final, assert_never

from rich.console import Console, Group
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from stackops.utils.installer_utils.constants import (
    BULK_INSTALL_FAILURE_EXCERPT_COUNT,
    BULK_INSTALL_FAILURE_TAIL_LINES,
    BULK_INSTALL_LOG_TAIL_BYTES,
    BULK_INSTALL_SLOWEST_COUNT,
    BULK_INSTALL_VERSION_WIDTH,
)
from stackops.utils.installer_utils.installer_bulk_models import BulkInstallStatus, FinishedInstall, PlannedInstall, RunningInstall


TERMINAL_NOISE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"""
)
FRAME_CHARACTERS: Final[str] = " \t|" + "".join(chr(code_point) for code_point in range(0x2500, 0x2580))
SPINNER_FRAMES: Final[str] = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
STATUS_ORDER: Final[tuple[BulkInstallStatus, ...]] = ("installed", "updated", "unchanged", "skipped", "failed")
STATUS_GLYPHS: Final[dict[BulkInstallStatus, tuple[str, str]]] = {
    "installed": ("✓", "green"),
    "updated": ("↑", "cyan"),
    "unchanged": ("=", "dim"),
    "skipped": ("·", "dim"),
    "failed": ("✗", "red"),
}


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"""{seconds:.1f}s"""
    minutes, remainder = divmod(int(seconds), 60)
    if minutes < 60:
        return f"""{minutes}m{remainder:02d}s"""
    hours, minutes = divmod(minutes, 60)
    return f"""{hours}h{minutes:02d}m"""


def format_path(path: Path) -> str:
    return f"""~/{path.relative_to(Path.home()).as_posix()}""" if path.is_relative_to(Path.home()) else str(path)


def read_log_tail(log_path: Path, line_count: int) -> list[str]:
    with log_path.open("rb") as log_file:
        log_size = log_file.seek(0, os.SEEK_END)
        log_file.seek(max(0, log_size - BULK_INSTALL_LOG_TAIL_BYTES))
        chunk = log_file.read()
    text = TERMINAL_NOISE_PATTERN.sub("", chunk.decode("utf-8", errors="replace"))
    visible_lines: list[str] = []
    for raw_line in text.split("\n"):
        redrawn_segments = [segment.strip(FRAME_CHARACTERS) for segment in raw_line.split("\r")]
        meaningful_segments = [segment for segment in redrawn_segments if any(character.isalnum() for character in segment)]
        if len(meaningful_segments) > 0:
            visible_lines.append(meaningful_segments[-1])
    return visible_lines[-line_count:]


def describe_finished_install(finished: FinishedInstall) -> tuple[BulkInstallStatus, str]:
    result = finished.result
    match result["kind"]:
        case "failed":
            return "failed", result["error"]
        case "skipped":
            return "skipped", result["detail"]
        case "same_version":
            version = _first_version_line(version_output=result["version"])
            return ("unchanged", f"""already {version}""") if finished.planned.was_installed else ("installed", version)
        case "updated":
            new_version = _first_version_line(version_output=result["newVersion"])
            if not finished.planned.was_installed:
                return "installed", new_version
            return "updated", f"""{_first_version_line(version_output=result["oldVersion"])} → {new_version}"""
        case _ as unreachable_kind:
            assert_never(unreachable_kind)


def _first_version_line(version_output: str) -> str:
    first_line = next((" ".join(line.split()) for line in version_output.splitlines() if line.strip() != ""), "")
    return first_line[:BULK_INSTALL_VERSION_WIDTH] if first_line != "" else "version not detected"


def print_finished_line(console: Console, finished: FinishedInstall, name_width: int) -> None:
    status, detail = describe_finished_install(finished=finished)
    symbol, style = STATUS_GLYPHS[status]
    line = Text()
    line.append(f""" {symbol} """, style=f"""bold {style}""")
    line.append(f"""{finished.planned.exe_name:<{name_width}}""", style="dim" if style == "dim" else "bold")
    line.append(f"""{format_duration(finished.seconds):>7}  """, style="dim")
    line.append(detail, style=style)
    console.print(line, no_wrap=True, overflow="ellipsis")


def render_live_view(
    running: list[RunningInstall], finished: list[FinishedInstall], queued_count: int, started_at: float, now: float, name_width: int
) -> Group:
    total_count = len(running) + len(finished) + queued_count
    status_counts = Counter(describe_finished_install(finished=item)[0] for item in finished)
    progress_text = Text()
    progress_text.append(f"""{len(finished)}/{total_count}""", style="bold")
    progress_text.append(f"""  {format_duration(now - started_at)}""", style="dim")
    for status in STATUS_ORDER:
        if status_counts[status] > 0:
            symbol, style = STATUS_GLYPHS[status]
            progress_text.append(f"""  {symbol} {status_counts[status]}""", style=style)
    progress_text.append(f"""  ·  {len(running)} running, {queued_count} queued""", style="dim")
    progress_row = Table.grid(padding=(0, 1))
    progress_row.add_row(ProgressBar(total=total_count, completed=len(finished), width=30), progress_text)
    running_lines: list[Text] = []
    for item in running:
        elapsed = now - item.started_at
        log_tail = read_log_tail(log_path=item.log_path, line_count=1)
        line = Text(no_wrap=True, overflow="ellipsis")
        line.append(f""" {SPINNER_FRAMES[int(elapsed * 10) % len(SPINNER_FRAMES)]} """, style="cyan")
        line.append(f"""{item.planned.exe_name:<{name_width}}""", style="bold")
        line.append(f"""{format_duration(elapsed):>7}  """, style="dim")
        line.append(log_tail[0] if len(log_tail) > 0 else "starting", style="dim")
        running_lines.append(line)
    return Group(Text(""), progress_row, *running_lines)


def render_nothing_to_install(console: Console, batch_label: str, planned_installs: list[PlannedInstall]) -> None:
    console.print()
    console.rule(Text(f"""📦 {batch_label}""", style="bold"), align="left", style="blue")
    console.print(Text(f""" · nothing to do, all {len(planned_installs)} apps are already installed (use --update to reinstall)""", style="dim"))
    console.print()


def render_bulk_header(console: Console, batch_label: str, planned_installs: list[PlannedInstall], parallel_jobs: int, log_dir: Path) -> None:
    to_run = [planned for planned in planned_installs if not planned.skip]
    skipped_names = [planned.exe_name for planned in planned_installs if planned.skip]
    locked_count = sum(1 for planned in to_run if planned.holds_system_installer_lock)
    console.print()
    console.rule(Text(f"""📦 {batch_label}""", style="bold"), align="left", style="blue")
    overview = f""" {len(to_run)} to install"""
    if len(to_run) > 1:
        overview += f""", {min(parallel_jobs, len(to_run))} at a time"""
    if locked_count > 1:
        overview += f""" ({locked_count} system installers and scripts run one at a time)"""
    console.print(Text(overview))
    if len(skipped_names) > 0:
        console.print(Text(f""" · {len(skipped_names)} already installed (use --update to reinstall): {", ".join(skipped_names)}""", style="dim"))
    console.print(Text(f""" logs → {format_path(path=log_dir)}""", style="dim"))


def render_bulk_summary(console: Console, batch_label: str, finished: list[FinishedInstall], wall_seconds: float, log_dir: Path) -> None:
    described = [(item, *describe_finished_install(finished=item)) for item in finished]
    status_counts = Counter(status for _item, status, _detail in described)
    console.print()
    app_count = f"""{len(finished)} app{"" if len(finished) == 1 else "s"}"""
    console.rule(Text(f"""📦 {batch_label} · {app_count} · {format_duration(wall_seconds)}""", style="bold"), align="left", style="blue")
    counts = [
        Text(f"""{STATUS_GLYPHS[status][0]} {status_counts[status]} {status}""", style=f"""bold {STATUS_GLYPHS[status][1]}""")
        for status in STATUS_ORDER
        if status_counts[status] > 0
    ]
    console.print(Text(" ") + Text("    ").join(counts))
    ran = [item for item in finished if item.log_path is not None]
    if len(ran) > 1:
        work_seconds = sum(item.seconds for item in ran)
        slowest = sorted(ran, key=lambda item: item.seconds, reverse=True)[:BULK_INSTALL_SLOWEST_COUNT]
        slowest_text = ", ".join(f"""{item.planned.exe_name} {format_duration(item.seconds)}""" for item in slowest)
        timing = f""" ⏱  {format_duration(work_seconds)} of installs in {format_duration(wall_seconds)} ({work_seconds / wall_seconds:.1f}× parallel) · slowest: {slowest_text}"""
        console.print(Text(timing, style="dim"))
    failures = [(item, detail, item.log_path) for item, status, detail in described if status == "failed" and item.log_path is not None]
    for item, detail, log_path in failures[:BULK_INSTALL_FAILURE_EXCERPT_COUNT]:
        console.print()
        console.print(Text.assemble((f""" ✗ {item.planned.exe_name}""", "bold red"), (f"""  {detail}""", "red")))
        for log_line in read_log_tail(log_path=log_path, line_count=BULK_INSTALL_FAILURE_TAIL_LINES):
            console.print(Text(f"""   │ {log_line}""", style="dim"), no_wrap=True, overflow="ellipsis")
        console.print(Text(f"""   ↳ {format_path(path=log_path)}""", style="dim"))
    failures_without_excerpt = failures[BULK_INSTALL_FAILURE_EXCERPT_COUNT:]
    if len(failures_without_excerpt) > 0:
        console.print()
        console.print(Text(f""" ✗ {len(failures_without_excerpt)} more failed: {", ".join(item.planned.exe_name for item, _detail, _log_path in failures_without_excerpt)}""", style="red"))
    console.print(Text(f""" logs → {format_path(path=log_dir)}""", style="dim"))
    console.print()
