from pathlib import Path

from stackops.scripts.python.helpers.helpers_seek.semantic.constants import (
    SEMANTIC_PREVIEW_SIZE_PERCENT,
    TV_CANCELLED_EXIT_CODE,
    TV_PREVIEW_CHROME_COLUMNS,
)
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticHit


def limit_distinct_hits(hits: list[SemanticHit], limit: int) -> list[SemanticHit]:
    kept: list[SemanticHit] = []
    for hit in hits:
        overlaps_kept_hit = any(
            hit.path == kept_hit.path and hit.start_line <= kept_hit.end_line and kept_hit.start_line <= hit.end_line
            for kept_hit in kept
        )
        if overlaps_kept_hit:
            continue
        kept.append(hit)
        if len(kept) == limit:
            break
    return kept


def choose_and_open_hit(hits: list[SemanticHit], edit: bool) -> None:
    import shutil
    import subprocess
    import tempfile

    from stackops.utils.cli_utils.interaction import require_interactive

    require_interactive("Interactive selection")
    working_directory = Path.cwd().resolve()
    preview_width = shutil.get_terminal_size().columns * SEMANTIC_PREVIEW_SIZE_PERCENT // 100 - TV_PREVIEW_CHROME_COLUMNS
    rows: list[str] = []
    for index, hit in enumerate(hits):
        display_path = hit.path.relative_to(working_directory) if hit.path.is_relative_to(working_directory) else hit.path
        label = f"""{display_path}:{hit.start_line}-{hit.end_line}  {hit.metric} {hit.value:.3f}"""
        rows.append(f"""{index}\t{hit.path}\t{hit.start_line}\t{hit.end_line}\t{hit.focus_line}\t{label}""")
    with tempfile.TemporaryDirectory(prefix="seek_semantic_") as temp_dir:
        entries_path = Path(temp_dir) / "entries.tsv"
        entries_path.write_text("\n".join(rows), encoding="utf-8")
        completed = subprocess.run(
            [
                "tv",
                "--source-command",
                f"""bat "{entries_path}" --style=plain --color=never --paging=never""",
                "--source-display",
                "{split:\t:5}",
                "--source-output",
                "{split:\t:0}",
                "--preview-command",
                f"""bat "{{split:\t:1}}" --color=always --style=numbers --wrap=character --terminal-width {preview_width} --highlight-line {{split:\t:4}} --line-range {{split:\t:2}}:{{split:\t:3}}""",
                "--preview-size",
                str(SEMANTIC_PREVIEW_SIZE_PERCENT),
            ],
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=False,
        )
    if completed.returncode not in (0, TV_CANCELLED_EXIT_CODE):
        raise SystemExit(completed.returncode)
    selected_index = completed.stdout.strip()
    if selected_index == "":
        print("❓ Selection cancelled.")
        return
    selected_hit = hits[int(selected_index)]
    selected_location = f"""{selected_hit.path}:{selected_hit.focus_line}"""
    if edit:
        subprocess.run(["hx", selected_location], check=True)
        return
    print(selected_location)
