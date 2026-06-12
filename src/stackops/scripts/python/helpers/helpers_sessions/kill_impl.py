from typing import Literal, TypedDict


class KilledTarget(TypedDict):
    action: Literal["session", "window", "pane"]
    session: str
    window: str
    detail: str


def choose_kill_target(
    backend: Literal["zellij", "tmux", "herdr"],
    name: str | None,
    kill_all: bool,
    idle: bool,
    window: bool,
) -> tuple[str, str | None, list[KilledTarget]]:
    match backend:
        case "zellij":
            from stackops.scripts.python.helpers.helpers_sessions._zellij_backend import choose_kill_target as _zellij

            return _zellij(name=name, kill_all=kill_all, idle=idle, window=window)
        case "tmux":
            from stackops.scripts.python.helpers.helpers_sessions._tmux_backend import choose_kill_target as _tmux

            return _tmux(name=name, kill_all=kill_all, idle=idle, window=window)
        case "herdr":
            from stackops.scripts.python.helpers.helpers_sessions._herdr_backend import choose_kill_target as _herdr

            return _herdr(name=name, kill_all=kill_all, idle=idle, window=window)
    raise ValueError(f"Unsupported backend: {backend}")