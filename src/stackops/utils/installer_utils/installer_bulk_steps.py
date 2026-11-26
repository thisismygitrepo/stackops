from pathlib import Path

from rich.console import Console
from rich.text import Text

from stackops.utils.installer_utils.constants import BULK_INSTALL_PATH_MARKER, BULK_INSTALL_STEP_MARKER, BULK_INSTALL_SYSTEM_READY_MARKER
from stackops.utils.installer_utils.installer_bulk_display import TERMINAL_NOISE_PATTERN, format_duration
from stackops.utils.installer_utils.installer_bulk_models import RunningInstall, StepProgress


def read_new_markers(log_path: Path, log_offset: int) -> tuple[list[str], bool, list[str], int]:
    with log_path.open("rb") as log_file:
        log_file.seek(log_offset)
        chunk = log_file.read()
    complete_length = chunk.rfind(b"\n") + 1
    lines = [line.strip() for line in TERMINAL_NOISE_PATTERN.sub("", chunk[:complete_length].decode("utf-8", errors="replace")).split("\n")]
    titles = [line.removeprefix(BULK_INSTALL_STEP_MARKER).strip() for line in lines if line.startswith(BULK_INSTALL_STEP_MARKER)]
    system_ready = any(line.startswith(BULK_INSTALL_SYSTEM_READY_MARKER) for line in lines)
    path_entries = [line.removeprefix(BULK_INSTALL_PATH_MARKER).strip() for line in lines if line.startswith(BULK_INSTALL_PATH_MARKER)]
    return titles, system_ready, path_entries, log_offset + complete_length


def print_step_line(console: Console, exe_name: str, title: str, seconds: float, failed: bool, name_width: int) -> None:
    line = Text()
    line.append(" ✗ " if failed else " › ", style="bold red" if failed else "dim")
    line.append(f"""{exe_name:<{name_width}}""", style="dim")
    line.append(f"""{format_duration(seconds):>7}  """, style="dim")
    line.append(title, style="red" if failed else "")
    console.print(line, no_wrap=True, overflow="ellipsis")


def advance_steps(running: RunningInstall, progress: StepProgress, now: float, console: Console, name_width: int) -> tuple[StepProgress, list[str]]:
    titles, system_ready, path_entries, log_offset = read_new_markers(log_path=running.log_path, log_offset=progress.log_offset)
    title = progress.title
    started_at = progress.started_at
    for next_title in titles:
        if title is not None:
            print_step_line(console=console, exe_name=running.planned.exe_name, title=title, seconds=now - started_at, failed=False, name_width=name_width)
        title = next_title
        started_at = now
    return StepProgress(log_offset=log_offset, title=title, started_at=started_at, system_ready=progress.system_ready or system_ready), path_entries
