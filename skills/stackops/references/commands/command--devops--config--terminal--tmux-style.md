# StackOps Command Reference: `devops config terminal tmux-style`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops config terminal tmux-style`. Follow child links one command segment at a time.

## Current Command

- Path: `devops config terminal tmux-style`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_config_terminal.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_config_tmux.get_app` via `tmux-style`
- Help: `Style tmux through the Oh My Tmux framework.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops config terminal tmux-style --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops config terminal tmux-style --help`

## Immediate Children

- [`devops config terminal tmux-style install-oh-my-tmux`](command--devops--config--terminal--tmux-style--install-oh-my-tmux.md) - command with no child commands. Help: `Install Oh My Tmux and link tmux to it.`.
- [`devops config terminal tmux-style apply-stackops-local`](command--devops--config--terminal--tmux-style--apply-stackops-local.md) - command with no child commands. Help: `Copy the StackOps Oh My Tmux local config.`.
- [`devops config terminal tmux-style preset`](command--devops--config--terminal--tmux-style--preset.md) - command with no child commands. Help: `Apply an Oh My Tmux color preset.`.
- [`devops config terminal tmux-style set-option`](command--devops--config--terminal--tmux-style--set-option.md) - command with no child commands. Help: `Set an Oh My Tmux tmux_conf_* option.`.
- [`devops config terminal tmux-style reload`](command--devops--config--terminal--tmux-style--reload.md) - command with no child commands. Help: `Reload tmux config.`.
- [`devops config terminal tmux-style status`](command--devops--config--terminal--tmux-style--status.md) - command with no child commands. Help: `Show tmux styling status.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
