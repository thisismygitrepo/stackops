import json
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import cast

SPINNER_FRAMES: list[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
TICK_SECONDS: float = 0.1
ACTIVITY_MAX_WIDTH: int = 60
BRIEF_MAX_WIDTH: int = 80
ARG_PRIORITY_KEYS: list[str] = ["command", "path", "pattern", "url", "query", "prompt", "file_text"]

DIM: str = "\x1b[90m"
CYAN: str = "\x1b[36m"
YELLOW: str = "\x1b[33m"
RED: str = "\x1b[31m"
GREEN: str = "\x1b[32m"
RESET: str = "\x1b[0m"
ERASE_LINE: str = "\r\x1b[2K"


@dataclass
class MonitorState:
    is_tty: bool
    lock: threading.Lock = field(default_factory=threading.Lock)
    stop: threading.Event = field(default_factory=threading.Event)
    status_drawn: bool = False
    mid_line: bool = False
    last_channel: str = ""
    activity: str = "starting"
    started_at: float = field(default_factory=time.monotonic)
    output_tokens: int = 0
    total_cost: float = 0.0
    interrupted: bool = False


def _style(state: MonitorState, code: str) -> str:
    return code if state.is_tty else ""


def _emit(state: MonitorState, fragment: str, style: str) -> None:
    opening = _style(state, style)
    closing = RESET if opening else ""
    sys.stdout.write(f"{opening}{fragment}{closing}")
    sys.stdout.flush()


def _write_fragment(state: MonitorState, fragment: str, style: str, channel: str) -> None:
    with state.lock:
        if state.status_drawn:
            sys.stdout.write(ERASE_LINE)
            state.status_drawn = False
        if state.mid_line and channel != state.last_channel:
            sys.stdout.write("\n")
        _emit(state, fragment, style)
        state.mid_line = not fragment.endswith("\n")
        state.last_channel = channel


def _write_line(state: MonitorState, line: str, style: str) -> None:
    _write_fragment(state, line + "\n", style, "line")


def _run_spinner(state: MonitorState) -> None:
    frame_idx = 0
    while not state.stop.wait(TICK_SECONDS):
        with state.lock:
            if state.mid_line:
                continue
            elapsed = int(time.monotonic() - state.started_at)
            frame = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
            activity = state.activity[:ACTIVITY_MAX_WIDTH]
            sys.stdout.write(f"\r{frame} {elapsed:4d}s · {activity}\x1b[K")
            sys.stdout.flush()
            state.status_drawn = True
        frame_idx += 1


def _set_activity(state: MonitorState, activity: str) -> None:
    state.activity = activity[:ACTIVITY_MAX_WIDTH]


def _brief_tool_args(args: dict[str, object]) -> str:
    for key in ARG_PRIORITY_KEYS:
        value = args.get(key)
        if value is not None:
            return str(value).replace("\n", " ")[:BRIEF_MAX_WIDTH]
    for value in args.values():
        if value is not None:
            return str(value).replace("\n", " ")[:BRIEF_MAX_WIDTH]
    return ""


def _handle_assistant_event(state: MonitorState, message_event: dict[str, object]) -> None:
    match message_event.get("type"):
        case "thinking_start":
            _set_activity(state, "thinking")
        case "thinking_delta":
            _set_activity(state, "thinking")
            delta = message_event.get("delta")
            if isinstance(delta, str):
                _write_fragment(state, delta, DIM, "thinking")
        case "text_start":
            _set_activity(state, "writing")
        case "text_delta":
            _set_activity(state, "writing")
            delta = message_event.get("delta")
            if isinstance(delta, str):
                _write_fragment(state, delta, "", "text")
        case "toolcall_start":
            _set_activity(state, f"calling {message_event.get("toolName", "tool")}")
        case _:
            pass


def _handle_message_end(state: MonitorState, message: dict[str, object]) -> None:
    if message.get("stopReason") == "error":
        error_message = str(message.get("errorMessage", "unknown error"))
        _write_line(state, f"✗ error: {error_message}", RED)
    if message.get("role") != "assistant":
        return
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return
    output = usage.get("output")
    if isinstance(output, int | float):
        state.output_tokens += int(output)
    cost = usage.get("cost")
    if isinstance(cost, dict):
        total = cost.get("total")
        if isinstance(total, int | float):
            state.total_cost += float(total)


def _handle_event(state: MonitorState, event: dict[str, object]) -> None:
    match event.get("type"):
        case "message_update":
            message_event = event.get("assistantMessageEvent")
            if isinstance(message_event, dict):
                _handle_assistant_event(state, cast(dict[str, object], message_event))
        case "message_end":
            message = event.get("message")
            if isinstance(message, dict):
                _handle_message_end(state, cast(dict[str, object], message))
        case "tool_execution_start":
            tool_name = str(event.get("toolName", "tool"))
            args_value = event.get("args")
            brief = _brief_tool_args(cast(dict[str, object], args_value)) if isinstance(args_value, dict) else ""
            label = f"{tool_name} {brief}".rstrip()
            _set_activity(state, label)
            _write_line(state, f"→ {label}", CYAN)
        case "tool_execution_end":
            _set_activity(state, "processing")
        case "auto_retry_start":
            attempt = event.get("attempt")
            max_attempts = event.get("maxAttempts")
            delay_ms = event.get("delayMs")
            _write_line(state, f"↻ retry {attempt}/{max_attempts} in {delay_ms}ms", YELLOW)
        case _:
            pass


def _finalize(state: MonitorState) -> None:
    with state.lock:
        if state.status_drawn:
            sys.stdout.write(ERASE_LINE)
        if state.mid_line:
            sys.stdout.write("\n")
        elapsed = time.monotonic() - state.started_at
        if state.interrupted:
            summary = f"✗ interrupted after {elapsed:.1f}s"
            _emit(state, summary, RED)
        else:
            summary = f"✓ done in {elapsed:.1f}s · {state.output_tokens} tok out · ${state.total_cost:.4f}"
            _emit(state, summary, GREEN)
        sys.stdout.write("\n")
        sys.stdout.flush()


def main() -> None:
    state = MonitorState(is_tty=sys.stdout.isatty())
    spinner: threading.Thread | None = None
    if state.is_tty:
        spinner = threading.Thread(target=_run_spinner, args=(state,), daemon=True)
        spinner.start()
    try:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if len(line) == 0:
                continue
            event: object = json.loads(line)
            if isinstance(event, dict):
                _handle_event(state, cast(dict[str, object], event))
    except KeyboardInterrupt:
        state.interrupted = True
    finally:
        state.stop.set()
        _finalize(state)


if __name__ == "__main__":
    main()
