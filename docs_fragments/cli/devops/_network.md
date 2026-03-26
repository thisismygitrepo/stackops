## network

Network management.

```bash
devops network [SUBCOMMAND] [ARGS]...
```

Network configuration, sharing, SSH setup, WiFi helpers, WARP helpers, and VS Code tunneling.

Current `devops network --help` exposes:

| Command | Description |
|---------|-------------|
| `share-terminal` | Share a terminal in the browser |
| `share-server` | Start a local or internet-facing file server |
| `send` | Send files or text from the current machine |
| `receive` | Receive files or text using a transfer code |
| `share-temp-file` | Upload one file to `temp.sh` |
| `ssh` | SSH server, key, and debugging subcommands |
| `show-address` | Show local and public addresses |
| `switch-public-ip` | Switch the public IP through Cloudflare WARP |
| `wifi-select` | Connect using configured or manually selected WiFi |
| `bind-wsl-port` | Bind a WSL port onto the Windows host |
| `open-wsl-port` | Open Windows Firewall rules for WSL ports |
| `link-wsl-windows` | Link WSL home and Windows home directories |
| `reset-cloudflare-tunnel` | Reconfigure Cloudflare tunnel execution |
| `add-ip-exclusion-to-warp` | Add WARP tunnel exclusions |
| `vscode-share` | Share a workspace with VS Code Tunnels or serve-web |

### share-terminal

Share a terminal through the browser.

```bash
devops network share-terminal [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--port`, `-p` | Port for the terminal server |
| `--username`, `-u` | Login username |
| `--password`, `-w` | Login password |
| `--no-auth`, `-n` | Disable authentication |
| `--start-command`, `-s` | Command to start in the shared terminal |
| `--ssl`, `-S` | Enable SSL |
| `--ssl-cert`, `-C` | Certificate file path |
| `--ssl-key`, `-K` | Key file path |
| `--ssl-ca`, `-A` | CA file for client certificate verification |
| `--over-internet`, `-i` | Expose via ngrok |
| `--install-dep`, `-D` | Install missing dependencies |

Example:

```bash
devops network share-terminal --port 7681
```

### share-server

Start a local or internet-facing file browser or static share server.

```bash
devops network share-server PATH [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--port`, `-p` | Port for the share server |
| `--username`, `-u` | Login username |
| `--password`, `-w` | Login password |
| `--no-auth`, `-na` | Disable authentication |
| `--bind`, `-a` | Bind address |
| `--over-internet`, `-i` | Expose via ngrok |
| `--backend`, `-b` | Backend choice from `filebrowser`, `miniserve`, `qrcp`, or `easy-sharing` |
| `--install-dep`, `-D` | Install missing dependencies |

Example:

```bash
devops network share-server ~/Downloads --backend miniserve --port 8080
```

### send

Send a file, directory, or text payload.

```bash
devops network send PATH [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--zip` | Zip the folder before sending |
| `--code`, `-c` | Explicit relay codephrase |
| `--text`, `-t` | Send text instead of file contents |
| `--qrcode`, `--qr` | Show the receive code as a QR code |
| `--backend`, `-b` | Transfer backend: `wormhole` or `croc` |
| `--install-dep`, `-D` | Install missing dependencies |

Examples:

```bash
devops network send ./build/output.zip
devops network send . --zip --backend wormhole
```

### receive

Receive files or text using a codephrase or explicit relay arguments.

```bash
devops network receive CODE_ARGS... [OPTIONS]
```

The argument may be a plain receive code such as `7121-donor-olympic-bicycle` or a full relay invocation such as `--relay 10.17.62.206:443 7121-donor-olympic-bicycle`.

Example:

```bash
devops network receive 7121-donor-olympic-bicycle
```

### share-temp-file

Upload one file to `temp.sh`.

```bash
devops network share-temp-file FILE_PATH
```

Example:

```bash
devops network share-temp-file ./report.txt
```

### ssh

SSH setup and troubleshooting lives under a nested Typer app:

```bash
devops network ssh [SUBCOMMAND] [ARGS]...
```

`devops network ssh --help` currently exposes:

| Command | Description |
|---------|-------------|
| `install-server` | Install the SSH server |
| `change-port` | Change the SSH port on Linux or WSL |
| `add-key` | Add an SSH public key locally or remotely |
| `debug` | Run SSH diagnostics |

#### install-server

```bash
devops network ssh install-server
```

Installs and configures the platform SSH server.

#### change-port

```bash
devops network ssh change-port --port 2222
```

Key option:

| Option | Description |
|--------|-------------|
| `--port`, `-p` | SSH port to use |

#### add-key

```bash
devops network ssh add-key [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--path` | Path to a public key file |
| `--choose`, `-c` | Choose from `~/.ssh/*.pub` |
| `--value`, `-v` | Paste the public key manually |
| `--github`, `-g` | Pull public keys from a GitHub username |
| `--remote`, `-r` | Deploy the key to a remote machine |

Examples:

```bash
devops network ssh add-key --choose
devops network ssh add-key --github thisismygitrepo
devops network ssh add-key --path ~/.ssh/id_ed25519.pub --remote myhost
```

#### debug

```bash
devops network ssh debug
```

Runs platform-specific SSH debugging helpers.

### show-address

Show local interface addresses plus the public IP address when available.

```bash
devops network show-address
```

Example:

```bash
devops network show-address
```

### switch-public-ip

Switch the public IP through Cloudflare WARP.

```bash
devops network switch-public-ip [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--wait`, `-w` | Seconds to wait between steps |
| `--max-trials`, `-m` | Maximum number of switch attempts |
| `--target-ip`, `-t` | Acceptable target IPs that skip the switch if already active |

Example:

```bash
devops network switch-public-ip --max-trials 5 --target-ip 203.0.113.10
```

### wifi-select

Connect to WiFi using the configured SSID or an interactive fallback flow.

```bash
devops network wifi-select [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--ssid`, `-n` | Configured SSID to try first |
| `--manual`, `-m` | Jump directly to manual selection |
| `--list`, `-l` | Only list visible networks |

Examples:

```bash
devops network wifi-select --list
devops network wifi-select --manual
```

### bind-wsl-port

Bind a WSL port onto the Windows host using `netsh interface portproxy`.

```bash
devops network bind-wsl-port --port 8080
```

### open-wsl-port

Open Windows Firewall rules for one or more WSL ports.

```bash
devops network open-wsl-port 8080,3000-3005,443
```

### link-wsl-windows

Link WSL home and Windows home directories.

```bash
devops network link-wsl-windows [OPTIONS]
```

Key option:

| Option | Description |
|--------|-------------|
| `--windows-username`, `-u` | Override the auto-detected Windows username |

### reset-cloudflare-tunnel

Print or run the commands needed to reconfigure Cloudflare tunnel execution.

```bash
devops network reset-cloudflare-tunnel [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--task`, `-t` | Required mode: `oneoff-shell-process`, `oneoff-background-process`, or `as-service` |
| `--tunnel-name`, `-n` | Tunnel name for one-off modes |

Examples:

```bash
devops network reset-cloudflare-tunnel --task oneoff-shell-process --tunnel-name my-tunnel
devops network reset-cloudflare-tunnel --task as-service
```

### add-ip-exclusion-to-warp

Add one or more IP exclusions to Cloudflare WARP.

```bash
devops network add-ip-exclusion-to-warp --ip 192.168.20.25,10.0.0.15
```

### vscode-share

Generate or run VS Code Tunnel and `code serve-web` commands.

```bash
devops network vscode-share ACTION [OPTIONS]
```

Supported actions from current help:

- `run`
- `install-service`
- `uninstall-service`
- `share-local`

Key options from current help:

| Option | Description |
|--------|-------------|
| `--name`, `-n` | Tunnel or service name |
| `--path`, `-p` | Server base path for `share-local` |
| `--host`, `-h` | Host for `share-local` |
| `--dir`, `-d` | Folder to open in `share-local` mode |
| `--extra-args`, `-e` | Extra CLI arguments to append |

Examples:

```bash
devops network vscode-share run --name labbox
devops network vscode-share install-service --name labbox
devops network vscode-share share-local --dir . --host 0.0.0.0
```

The nested help screens render shortened usage such as `devops share-server ...`, `devops ssh ...`, or `devops vscode-share ...`, but the full entrypoints remain under `devops network ...`.

---
