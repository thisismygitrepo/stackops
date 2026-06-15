from typing import Literal, TypedDict


class KilledTarget(TypedDict):
    action: Literal["session", "window", "pane"]
    session: str
    window: str
    detail: str


def choose_kill_target(
    backend: Literal["tmux", "herdr"],
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
    delete: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    match backend:
        case "tmux":
            if delete:
                return ("error", "--delete is only supported by the Herdr backend.", [])
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import choose_kill_target as _tmux

            return _tmux(name=name, kill_all=kill_all, idle=idle, window=window)
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions._herdr_backend import choose_kill_target as _herdr

            return _herdr(name=name, kill_all=kill_all, idle=idle, window=window, delete=delete)
    raise ValueError(f"Unsupported backend: {backend}")
