from typing import Literal


def choose_kill_target(
    backend: Literal["zellij", "tmux"],
    name: str | None,
    kill_all: bool = False,
    window: bool = False,
) -> tuple[str, str | None]:
    match backend:
        case "zellij":
            from machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend import choose_kill_target as _zellij

            return _zellij(name=name, kill_all=kill_all, window=window)
        case "tmux":
            from machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend import choose_kill_target as _tmux

            return _tmux(name=name, kill_all=kill_all, window=window)
    raise ValueError(f"Unsupported backend: {backend}")
