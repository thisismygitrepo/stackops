from typing import Literal


def choose_kill_target(
    backend: Literal["zellij", "tmux"],
    name: str | None,
    window: bool = False,
) -> tuple[str, str | None]:
    match backend:
        case "zellij":
            from machineconfig.scripts.python.helpers.helpers_sessions._zellij_backend import choose_kill_target as _zellij

            return _zellij(name=name, window=window)
        case "tmux":
            from machineconfig.scripts.python.helpers.helpers_sessions._tmux_backend import choose_kill_target as _tmux

            return _tmux(name=name, window=window)
    raise ValueError(f"Unsupported backend: {backend}")
