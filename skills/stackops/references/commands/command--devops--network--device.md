# StackOps Command Reference: `devops network device`

Regenerated from `src/stackops/scripts/python/graph/cli_graph.json` on 2026-06-21.

This page expands exactly one level below `devops network device`. Follow child links one command segment at a time.

## Current Command

- Path: `devops network device`
- Kind: `group`
- Source: `src/stackops/scripts/python/helpers/helpers_devops/cli_nw.py` -> `stackops.scripts.python.helpers.helpers_devops.cli_device.get_app` via `device`
- Help: `🖥 <d> Device subcommands`

## Help Commands

- `UV_CACHE_DIR=/tmp/uv-cache uv run devops network device --help`
- `UV_CACHE_DIR=/tmp/uv-cache uv run stackops devops network device --help`

## Immediate Children

- [`devops network device switch-public-ip`](command--devops--network--device--switch-public-ip.md) - command with no child commands. Help: `🔁 <s> Switch public IP address (Cloudflare WARP)`.
- [`devops network device wifi-select`](command--devops--network--device--wifi-select.md) - command with no child commands. Help: `📶 <w> WiFi connection utility.`.
- [`devops network device bind-wsl-port`](command--devops--network--device--bind-wsl-port.md) - command with no child commands. Help: `🔌 <b> Bind WSL port to Windows host`.
- [`devops network device open-wsl-port`](command--devops--network--device--open-wsl-port.md) - command with no child commands. Help: `🔥 <o> Open Windows firewall ports for WSL.`.
- [`devops network device link-wsl-windows`](command--devops--network--device--link-wsl-windows.md) - command with no child commands. Help: `🔗 <l> Link WSL home and Windows home directories.`.
- [`devops network device reset-cloudflare-tunnel`](command--devops--network--device--reset-cloudflare-tunnel.md) - command with no child commands. Help: `☁ <r> Reset Cloudflare tunnel service`.
- [`devops network device add-ip-exclusion-to-warp`](command--devops--network--device--add-ip-exclusion-to-warp.md) - command with no child commands. Help: `🚫 <p> Add IP exclusion to WARP`.

## Notes

- Developer-only command groups under `devops self` depend on the developer checkout at `~/code/stackops`.
- Callback groups are invoked as the group command itself when their command reference has no children.
- The generated graph stores aliases on each node. Use `src/stackops/scripts/python/graph/cli_graph.json` when alias details matter.
- Docs may lag source. Prefer command paths and behavior verified from current Typer source and `--help` output.
