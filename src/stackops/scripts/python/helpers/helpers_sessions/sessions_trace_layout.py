from dataclasses import dataclass
from typing import TYPE_CHECKING

FOOTER_HEIGHT = 1
SESSIONS_BUDGET_SHARE = 3

if TYPE_CHECKING:
    from rich.console import Console, RenderableType


@dataclass(frozen=True, slots=True)
class TraceLayout:
    show_panes: bool
    sessions_visible: int | None
    pending_visible: int | None
    settled_visible: int | None
    footer_parts: tuple[str, ...]


def measure_lines(console: "Console", renderable: "RenderableType") -> int:
    return len(console.render_lines(renderable, console.options, pad=False, new_lines=False))


def plan_trace_layout(
    console_height: int,
    header_height: int,
    warnings_height: int,
    sessions_chrome: int,
    panes_chrome: int,
    session_count: int,
    pending_count: int,
    settled_count: int,
    placeholder_rows: int,
) -> TraceLayout:
    sessions_full_height = sessions_chrome + session_count
    panes_full_height = panes_chrome + pending_count + settled_count + placeholder_rows
    if header_height + warnings_height + sessions_full_height + panes_full_height <= console_height:
        return TraceLayout(
            show_panes=True,
            sessions_visible=None,
            pending_visible=None,
            settled_visible=None,
            footer_parts=(),
        )

    rows_budget = max(1, console_height - header_height - warnings_height - sessions_chrome - panes_chrome - FOOTER_HEIGHT)
    sessions_cap = max(1, rows_budget // SESSIONS_BUDGET_SHARE)
    if session_count <= sessions_cap:
        sessions_visible = session_count
        sessions_overflow = 0
    else:
        sessions_visible = max(0, sessions_cap - 1)
        sessions_overflow = session_count - sessions_visible

    remaining = rows_budget - sessions_visible - (1 if sessions_overflow > 0 else 0)
    remaining = max(0, remaining)
    if remaining == 0:
        footer_parts = tuple(
            part
            for part in (
                f"+{sessions_overflow} more sessions" if sessions_overflow > 0 else None,
                "+pane details hidden",
            )
            if part is not None
        )
        return TraceLayout(
            show_panes=False,
            sessions_visible=sessions_visible,
            pending_visible=0,
            settled_visible=0,
            footer_parts=footer_parts,
        )

    remaining = max(0, remaining - placeholder_rows)
    if pending_count <= remaining:
        pending_visible = pending_count
        pending_overflow = 0
    else:
        pending_visible = max(0, remaining - 1)
        pending_overflow = pending_count - pending_visible

    remaining = max(0, remaining - pending_visible - (1 if pending_overflow > 0 else 0))
    settled_visible = min(settled_count, remaining)
    settled_overflow = settled_count - settled_visible

    footer_parts = (f"+{settled_overflow} more settled panes",) if settled_overflow > 0 else ()
    return TraceLayout(
        show_panes=True,
        sessions_visible=sessions_visible,
        pending_visible=pending_visible,
        settled_visible=settled_visible,
        footer_parts=footer_parts,
    )
