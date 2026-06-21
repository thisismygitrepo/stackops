# StackOps Command Reference: `devops network`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops network`. Follow child links one command segment at a time.

## Current Command

- Path: `devops network`
- Kind: `group`
- Source: `src/stackops/scripts/python/devops.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_nw.get_app` via `network`
- Help: `🌐 <n> Network management`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops network --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops network --help`

## Immediate Children

- [`devops network share-terminal`](command--devops--network--share-terminal.md) - command with no child commands. Help: `📡 <t> Share terminal via web browser`.
- [`devops network share-server`](command--devops--network--share-server.md) - command with no child commands. Help: `🌐 <s> Start local/global server to share files/folders via web browser`.
- [`devops network send`](command--devops--network--send.md) - command with no child commands. Help: `📁 <f> send files from here.`.
- [`devops network receive`](command--devops--network--receive.md) - command with no child commands. Help: `📁 <r> receive files to here.`.
- [`devops network share-temp-file`](command--devops--network--share-temp-file.md) - command with no child commands. Help: `🌡 <T> Share a file via temp.sh`.
- [`devops network ssh`](command--devops--network--ssh.md) - group with 4 immediate child commands. Help: `🔐 <S> SSH subcommands`.
- [`devops network device`](command--devops--network--device.md) - group with 7 immediate child commands. Help: `🖥 <d> Device subcommands`.
- [`devops network show-address`](command--devops--network--show-address.md) - command with no child commands. Help: `📌 <a> Show this computer addresses on network`.
- [`devops network vscode-share`](command--devops--network--vscode-share.md) - command with no child commands. Help: `💻 <v> Share workspace via VS Code Tunnels`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
