# StackOps Command Reference: `devops config`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops config`. Follow child links one command segment at a time.

## Current Command

- Path: `devops config`
- Kind: `group`
- Source: `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_config.get_app` via `config`
- Help: `🔩 <c> Configuration management`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops config --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops config --help`

## Immediate Children

- [`devops config sync`](command--devops--config--sync.md) - command with no child commands. Help: `🔄 <s> Sync dotfiles.`.
- [`devops config register`](command--devops--config--register.md) - command with no child commands. Help: `📇 <r> Register dotfiles against user mapper.yaml`.
- [`devops config edit`](command--devops--config--edit.md) - command with no child commands. Help: `📝 <e> Open dotfiles mapper.yaml in nano, hx, or code.`.
- [`devops config export-dotfiles`](command--devops--config--export-dotfiles.md) - command with no child commands. Help: `📤 <E> Export dotfiles for migration to new machine.`.
- [`devops config import-dotfiles`](command--devops--config--import-dotfiles.md) - command with no child commands. Help: `📥 <I> Import dotfiles from exported archive.`.
- [`devops config terminal`](command--devops--config--terminal.md) - group with 7 immediate child commands. Help: `🐚 <t> Configure your terminal profile.`.
- [`devops config interactive`](command--devops--config--interactive.md) - command with no child commands. Help: `🤖 <i> Interactive configuration of machine.`.
- [`devops config copy-assets`](command--devops--config--copy-assets.md) - command with no child commands. Help: `📋 <c> Copy asset files from library to machine.`.
- [`devops config secrets`](command--devops--config--secrets.md) - group with 5 immediate child commands. Help: `f'🔐 <S> {secrets_module.SECRETS_HELP}'`.
- [`devops config dump`](command--devops--config--dump.md) - command with no child commands. Help: `📦 <d> Dump example configuration files and init scripts.`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
