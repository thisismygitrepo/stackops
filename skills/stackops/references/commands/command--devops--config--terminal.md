# StackOps Command Reference: `devops config terminal`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops config terminal`. Follow child links one command segment at a time.

## Current Command

- Path: `devops config terminal`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_config.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_config_terminal.get_app` via `terminal`
- Help: `🐚 <t> Configure your terminal profile.`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops config terminal --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops config terminal --help`

## Immediate Children

- [`devops config terminal config-shell`](command--devops--config--terminal--config-shell.md) - command with no child commands. Help: `Create or configure a shell profile.`.
- [`devops config terminal starship-theme`](command--devops--config--terminal--starship-theme.md) - command with no child commands. Help: `Select starship prompt theme.`.
- [`devops config terminal pwsh-theme`](command--devops--config--terminal--pwsh-theme.md) - command with no child commands. Help: `Select powershell prompt theme.`.
- [`devops config terminal wezterm-theme`](command--devops--config--terminal--wezterm-theme.md) - command with no child commands. Help: `Select WezTerm terminal theme.`.
- [`devops config terminal ghostty-theme`](command--devops--config--terminal--ghostty-theme.md) - command with no child commands. Help: `Select Ghostty terminal theme.`.
- [`devops config terminal windows-terminal-theme`](command--devops--config--terminal--windows-terminal-theme.md) - command with no child commands. Help: `Select Windows Terminal color scheme.`.
- [`devops config terminal tmux-style`](command--devops--config--terminal--tmux-style.md) - group with 6 immediate child commands. Help: `Style tmux through the Oh My Tmux framework.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
