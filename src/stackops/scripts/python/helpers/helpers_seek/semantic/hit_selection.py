from pathlib import Path

from stackops.scripts.python.helpers.helpers_seek.semantic.constants import SEMANTIC_PREVIEW_SIZE_PERCENT
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
    import subprocess

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    working_directory = Path.cwd().resolve()
    hits_by_label: dict[str, SemanticHit] = {}
    previews_by_label: dict[str, str] = {}
    for hit in hits:
        display_path = hit.path.relative_to(working_directory) if hit.path.is_relative_to(working_directory) else hit.path
        location = f"""{display_path}:{hit.start_line}-{hit.end_line}"""
        label = f"""{location}  {hit.metric} {hit.value:.3f}"""
        hits_by_label[label] = hit
        previews_by_label[label] = f"""{location}
{hit.metric}: {hit.value:.4f}

{hit.content}"""

    suffixes = {hit.path.suffix for hit in hits}
    selected_label = choose_from_dict_with_preview(
        options_to_preview_mapping=previews_by_label,
        extension=suffixes.pop() if len(suffixes) == 1 else None,
        multi=False,
        preview_size_percent=SEMANTIC_PREVIEW_SIZE_PERCENT,
    )
    if selected_label is None:
        print("❓ Selection cancelled.")
        return
    selected_hit = hits_by_label[selected_label]
    selected_location = f"""{selected_hit.path}:{selected_hit.focus_line}"""
    if edit:
        subprocess.run(["hx", selected_location], check=True)
        return
    print(selected_location)
