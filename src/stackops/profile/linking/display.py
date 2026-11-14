import shutil
import subprocess
from collections import Counter
from itertools import takewhile
from pathlib import Path
from typing import Final, Literal, assert_never, get_args

from rich.console import Console
from rich.text import Text

from stackops.profile.dotfiles_constants import SYNC_COUNT_WIDTH, SYNC_FAILURE_EXCERPT_COUNT
from stackops.profile.linking.operations import ActionType, OperationRecord, OperationResult
from stackops.profile.linking.options import DIRECTION_STRICT

type SyncOutcome = Literal["failed", "replaced", "moved", "new", "unchanged"]

OUTCOMES_BY_IMPORTANCE: Final[tuple[SyncOutcome, ...]] = get_args(SyncOutcome.__value__)


def classify_action(action: ActionType) -> SyncOutcome:
    match action:
        case "error" | "conflict":
            return "failed"
        case "relinking" | "relinking_to_new_target" | "fixing_broken_link" | "backupConfigDefaultPath" | "backing_up_source" | "backing_up_target":
            return "replaced"
        case "move2selfManagedPath" | "moving_to_target" | "relink2newSelfManagedPath":
            return "moved"
        case "new_link" | "newLinkAndSelfManagedPath" | "new_link_and_target" | "linking" | "copying":
            return "new"
        case "already_linked" | "identical_files":
            return "unchanged"
        case _ as unreachable_action:
            assert_never(unreachable_action)


def outcome_glyph(outcome: SyncOutcome) -> tuple[str, str]:
    match outcome:
        case "failed":
            return "✗", "red"
        case "replaced":
            return "↑", "cyan"
        case "moved":
            return "→", "magenta"
        case "new":
            return "+", "green"
        case "unchanged":
            return "=", "dim"
        case _ as unreachable_outcome:
            assert_never(unreachable_outcome)


def format_path(path: Path) -> str:
    return str(Path("~").joinpath(path.relative_to(Path.home()))) if path.is_relative_to(Path.home()) else str(path)


def print_operation_detail(console: Console, label: str, result: OperationResult, config_file_default_path: Path, config_file_self_managed_path: Path) -> None:
    symbol, style = outcome_glyph(outcome=classify_action(action=result["action"]))
    line = Text()
    line.append(f""" {symbol} {label}""", style=f"""bold {style}""")
    line.append(f"""  {format_path(path=config_file_default_path)}""")
    line.append(" ⇄ ", style="dim")
    line.append(format_path(path=config_file_self_managed_path))
    console.print(line, soft_wrap=True)
    for detail_line in result["details"].splitlines():
        console.print(Text(f"""   │ {detail_line}""", style="dim"), soft_wrap=True)
    if result["action"] != "conflict":
        return
    if shutil.which("delta") is None:
        console.print(Text("""   │ install delta to see the differences here""", style="dim"))
        return
    subprocess.run(["delta", "--paging", "never", "--side-by-side", str(config_file_default_path), str(config_file_self_managed_path)], check=False)


def print_program_line(console: Console, program_name: str, records: list[OperationRecord], name_width: int) -> None:
    counts = Counter(classify_action(action=record["action"]) for record in records)
    present: list[SyncOutcome] = [outcome for outcome in OUTCOMES_BY_IMPORTANCE if counts[outcome] > 0]
    symbol, style = outcome_glyph(outcome=present[0]) if len(present) > 0 else ("·", "dim")
    default_path_parts = [Path(record["defaultPath"]).parts for record in records]
    shared_parts = [column[0] for column in takewhile(lambda column: len(set(column)) == 1, zip(*default_path_parts))]
    line = Text()
    line.append(f""" {symbol} """, style=f"""bold {style}""")
    line.append(f"""{program_name:<{name_width}}""", style="dim" if style == "dim" else "bold")
    if len(present) == 0:
        line.append(f"""{"":>{SYNC_COUNT_WIDTH - 1}}nothing to sync""", style="dim")
    for index, outcome in enumerate(present):
        count_text = f"""{counts[outcome]:>{SYNC_COUNT_WIDTH}}""" if index == 0 else f""", {counts[outcome]}"""
        line.append(f"""{count_text} {outcome}""", style=outcome_glyph(outcome=outcome)[1])
    if len(shared_parts) > 0:
        line.append(f"""  {format_path(path=Path(*shared_parts))}""", style="dim")
    console.print(line, no_wrap=True, overflow="ellipsis")


def render_sync_summary(console: Console, direction: DIRECTION_STRICT, program_count: int, records: list[OperationRecord], csv_path: Path) -> None:
    counts = Counter(classify_action(action=record["action"]) for record in records)
    program_label = f"""{program_count} program{"" if program_count == 1 else "s"}"""
    file_label = f"""{len(records)} file{"" if len(records) == 1 else "s"}"""
    console.print()
    console.rule(Text(f"""🔗 dotfiles sync {direction} · {program_label} · {file_label}""", style="bold"), align="left", style="blue")
    totals = [
        Text(f"""{outcome_glyph(outcome=outcome)[0]} {counts[outcome]} {outcome}""", style=f"""bold {outcome_glyph(outcome=outcome)[1]}""")
        for outcome in OUTCOMES_BY_IMPORTANCE
        if counts[outcome] > 0
    ]
    console.print(Text(" ") + Text("    ").join(totals))
    failures = [record for record in records if classify_action(action=record["action"]) == "failed"]
    for record in failures[:SYNC_FAILURE_EXCERPT_COUNT]:
        console.print()
        print_operation_detail(
            console=console,
            label=f"""{record["program"]} · {record["file_key"]}""",
            result=record,
            config_file_default_path=Path(record["defaultPath"]),
            config_file_self_managed_path=Path(record["selfManaged"]),
        )
    if len(failures) > SYNC_FAILURE_EXCERPT_COUNT:
        console.print()
        console.print(Text(f""" ✗ {len(failures) - SYNC_FAILURE_EXCERPT_COUNT} more failed, every one is listed in the log""", style="red"))
    console.print(Text(f""" log → {format_path(path=csv_path)}""", style="dim"), soft_wrap=True)
    console.print()
