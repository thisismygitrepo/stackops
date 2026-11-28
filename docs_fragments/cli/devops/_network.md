## network

Network management.

```bash
devops network [SUBCOMMAND] [ARGS]...
```

Network configuration, sharing, SSH setup, Cloudflare/WARP operations, device-focused WiFi/WSL helpers, and VS Code tunneling.

Current `devops network --help` exposes:

| Command | Description |
|---------|-------------|
| `share-terminal` | Share a terminal in the browser |
| `share-server` | Start a local or internet-facing file server |
| `send` | Send files or text from the current machine |
| `receive` | Receive files or text using a transfer code |
| `share-temp-file` | Upload one file to `temp.sh` |
| `ssh` | SSH server, key, debugging, and port-mapping subcommands |
| `cloudflare` | Cloudflare Tunnel and WARP subcommands |
| `device` | Device-oriented WiFi and WSL subcommands |
| `show-address` | Show local and public addresses |
| `vscode-share` | Share a workspace with VS Code Tunnels or serve-web |

### share-terminal

Share a terminal through the browser.

```bash
devops network share-terminal [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--port`, `-p` | Port for the terminal server (default: any free port) |
| `--username`, `-u` | Login username (default: current user) |
| `--password`, `-w` | Login password (default: configured quick password) |
| `--password-file`, `-f` | Read the access password from a file; `-` reads stdin |
| `--password-env`, `-E` | Environment variable containing the access password |
| `--no-auth`, `-n` | Disable authentication |
| `--start-command`, `-s` | Command to start in the shared terminal |
| `--ssl`, `-S` | Enable SSL |
| `--ssl-cert`, `-C` | Certificate file path |
| `--ssl-key`, `-K` | Key file path |
| `--ssl-ca`, `-A` | CA file for client certificate verification |
| `--over-internet`, `-i` | Expose via ngrok |
| `--install-dep`, `-D` | Install missing dependencies |
| `--background`, `-B` | Keep the server running after the command exits |
| `--json`, `-j` | Print ready URLs, process IDs, and log files as JSON |
| `--timeout`, `-T` | Seconds to wait for each service to become ready (default 30) |

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
| `--port`, `-p` | Port for the share server (default: any free port) |
| `--username`, `-u` | Login username (default: current user) |
| `--password`, `-w` | Login password (default: configured quick password) |
| `--password-file`, `-f` | Read the access password from a file; `-` reads stdin |
| `--password-env`, `-E` | Environment variable containing the access password |
| `--no-auth`, `-n` | Disable authentication |
| `--host`, `-H` | Bind address (default `0.0.0.0`) |
| `--over-internet`, `-i` | Expose via ngrok |
| `--backend`, `-b` | Backend choice from `filebrowser` (default), `miniserve`, `qrcp`, or `easy-sharing` |
| `--install-dep`, `-D` | Install missing dependencies |
| `--background`, `-B` | Keep the server running after the command exits |
| `--json`, `-j` | Print ready URLs, process IDs, and log files as JSON |
| `--timeout`, `-T` | Seconds to wait for each service to become ready (default 30) |

Example:

```bash
devops network share-server ~/Downloads --backend miniserve --port 8080
```

### send

Send a file, directory, or text payload.

```bash
devops network send [PATH] [OPTIONS]
```

`PATH` is required unless `--text` is given; the two cannot be combined.

Key options from current help:

| Option | Description |
|--------|-------------|
| `--zip`, `-z` | Zip the folder before sending (croc only) |
| `--code`, `-c` | Explicit relay codephrase |
| `--text`, `-t` | Send text instead of file contents |
| `--qrcode`, `--qr`, `-q` | Show the receive code as a QR code (croc only) |
| `--backend`, `-b` | Transfer backend: `croc` (default) or `wormhole` |
| `--local-relay`, `-l` | Point croc at this machine's LAN IPv4 address on port 443 as its relay instead of croc's public relay (croc only); StackOps does not start a relay there |
| `--encryption`, `-e` | GPG-encrypt the file or directory before sending: `symmetric`/`s` or `asymmetric`/`a` |
| `--password`, `-p` | Symmetric GPG password; prompted when omitted |
| `--recipient`, `-r` | Asymmetric GPG recipient key; defaults to your own key |
| `--install-dep`, `-D` | Install missing dependencies |
| `--json`, `-j` | Emit JSON Lines with the transfer code and PID, then the completion status |
| `--timeout`, `-T` | Maximum seconds to wait for the transfer to complete |

croc uses its public relay unless `--local-relay` is given; the receive command printed for a local relay carries the `--relay` address. `--local-relay` only passes `--relay <LAN IPv4>:443` to croc: StackOps starts no relay process of its own, so a croc relay has to be listening on that address for croc to use it.

`--code` only secures the transfer. `--encryption` encrypts the payload itself, so it arrives as a `.gpg` file (a directory as `.zip.gpg`) that stays encrypted until the receiver runs `devops data decrypt`. It applies to files and directories, not `--text`.

Examples:

```bash
devops network send ./build/output.zip
devops network send . --zip
devops network send ./notes.txt --backend wormhole
devops network send ./build/output.zip --local-relay
devops network send ./secrets --encryption symmetric
devops network send ./report.pdf --encryption asymmetric --recipient alice@example.com
```

### receive

Receive files or text with croc using a codephrase or explicit relay arguments.

```bash
devops network receive [CODE_ARGS...] [OPTIONS]
```

The argument may be a plain receive code such as `7121-donor-olympic-bicycle` or a full relay invocation such as `--relay 10.17.62.206:443 7121-donor-olympic-bicycle`; put `--` before relay arguments so they are passed through. `--install-dep`, `-D` installs croc when it is missing. A transfer sent with `--backend wormhole` is received with `uvx --from magic-wormhole wormhole receive <code>` instead.

`--propose`, `-p` lets the receiving side choose the secrets: it takes no code argument, makes up a 32-character code and a 32-character encryption password, and shows a QR code holding the matching `devops network send <path> --code ... --encryption symmetric --password ...` command. It then waits for the sender, retrying every few seconds until one connects (`Ctrl+C` stops), and decrypts what arrives into the current directory. A sender that starts in the instant after a retry can stop at once with `EOF`; running the send command again is enough. It needs `croc` and `gpg`, and `uv` fetches the `qrcode` package the first time a QR code is drawn. It receives files and folders only; a transfer that was not sent with `--encryption symmetric` is reported as an error and kept as received. `--json`, `-j` (only with `--propose`) prints the code, password and send command as one JSON line instead of the QR code, and the decrypted paths as a second JSON line when the transfer completes.

Examples:

```bash
devops network receive 7121-donor-olympic-bicycle
devops network receive -- --relay 10.17.62.206:443 7121-donor-olympic-bicycle
devops network receive --propose
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
| `map-port` | Map a remote TCP port to local loopback over SSH |

#### install-server

```bash
devops network ssh install-server
```

Installs the platform SSH server where needed, then enables and starts it: on Linux the distribution's OpenSSH server package and its service, on macOS the built-in Remote Login, and on Windows (as Administrator) the OpenSSH Server capability, an automatic `sshd` service, and an inbound firewall rule for TCP port 22. It does not edit `sshd_config`.

#### change-port

```bash
devops network ssh change-port --port 2222
```

Key option:

| Option | Description |
|--------|-------------|
| `--port`, `-p` | SSH port to use (default 2222) |

#### add-key

```bash
devops network ssh add-key [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--path`, `-p` | Path to a public key file |
| `--choose`, `-c` | Choose from `~/.ssh/*.pub` |
| `--value`, `-v` | Paste the public key manually |
| `--github`, `-g` | Pull public keys from a GitHub username |
| `--remote`, `-r` | Deploy the key to a remote machine (SSH config name or `user@host:port`) |
| `--password-file`, `-f` | Read the SSH password or key passphrase from a file; `-` reads stdin |
| `--password-env`, `-E` | Environment variable containing the SSH password or key passphrase |

Examples:

```bash
devops network ssh add-key --choose
devops network ssh add-key --github thisismygitrepo
devops network ssh add-key --path ~/.ssh/id_ed25519.pub --remote myhost
```

#### debug

```bash
devops network ssh debug [OPTIONS]
```

Runs platform-specific SSH debugging helpers.

Key options from current help:

| Option | Description |
|--------|-------------|
| `--json`, `-j` | Print the diagnostic checks and readiness summary as JSON |
| `--client-host`, `-H` | Resolved SSH client host name for `Match` rules |
| `--client-address`, `-c` | SSH client source IP address for `Match` rules |
| `--local-address`, `-a` | Server local IP address receiving the connection |
| `--local-port`, `-p` | Server local TCP port receiving the connection |
| `--routing-domain`, `-r` | Routing domain for `Match RDomain` rules |

#### map-port

Map a remote TCP port to a local loopback port through SSH.

```bash
devops network ssh map-port DESTINATION REMOTE_PORT [OPTIONS]
```

Key options:

| Option | Description |
|--------|-------------|
| `--local-port`, `-l` | Local TCP port; defaults to the remote port |
| `--open-browser`, `-b` | Open the mapped local HTTP address once the tunnel is ready |
| `--background`, `-B` | Keep the SSH tunnel running after the command exits |
| `--json`, `-j` | Print the ready local URL, PID, and log file as JSON |
| `--timeout`, `-T` | Seconds to wait for SSH forwarding readiness (default 30) |

Example:

```bash
devops network ssh map-port workstation 8000 --local-port 9000 --open-browser
```

### cloudflare

Cloudflare Tunnel and WARP actions live under a dedicated Typer app:

```bash
devops network cloudflare [SUBCOMMAND] [ARGS]...
```

`devops network cloudflare --help` currently exposes:

| Command | Description |
|---------|-------------|
| `switch-public-ip` | Switch the public IP through Cloudflare WARP |
| `connect-warp` | Connect WARP, repairing its service and registration, and show the IP before and after |
| `run-tunnel` | Run a tunnel in the foreground or as a transient background service |
| `reinstall-tunnel-service` | Reinstall the persistent Cloudflare tunnel service |
| `add-ip-exclusion-to-warp` | Add WARP tunnel exclusions |
| `tunnel-status` | Show tunnel redundancy, connector services, versions, and routes |
| `update-connectors` | Rolling-update Cloudflare Tunnel connectors |
| `sync-routes` | Copy selected ingress routes without tunnel credentials |

#### switch-public-ip

Switch the public IP through Cloudflare WARP.

```bash
devops network cloudflare switch-public-ip [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--wait`, `-w` | Seconds to wait between steps (default 2) |
| `--max-trials`, `-m` | Maximum number of switch attempts (default 10) |
| `--target-ip`, `-t` | Acceptable target IPs that skip the switch if already active; repeat for several |
| `--json`, `-j` | Print the final public IP and status as JSON |

Example:

```bash
devops network cloudflare switch-public-ip --max-trials 5 --target-ip 203.0.113.10
```

#### connect-warp

Connect Cloudflare WARP if it is not already connected. The command installs `warp-cli` when it is missing, starts the `warp-svc` service when it is down (Linux only; elsewhere it stops and asks you to start the service), registers the device when the registration is missing, replaces a stale registration, accepts the WARP Terms of Service, and compares the status and the public IP, location, and network before and after.

```bash
devops network cloudflare connect-warp [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--update`, `-u` | Update `warp-cli` to the latest release before connecting |
| `--timeout`, `-t` | Seconds to wait for WARP to connect |
| `--wait`, `-w` | Seconds between status checks |

Example:

```bash
devops network cloudflare connect-warp --update
```

#### run-tunnel

Run a Cloudflare tunnel in the foreground, or use a transient systemd service with `--background`. The command confirms before running unless `--yes` is passed.

```bash
devops network cloudflare run-tunnel [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--background`, `-b` | Run as a transient systemd service |
| `--tunnel-name`, `-n` | Tunnel name to run |
| `--yes`, `-y` | Run without confirmation |

Examples:

```bash
devops network cloudflare run-tunnel --tunnel-name my-tunnel
devops network cloudflare run-tunnel --tunnel-name my-tunnel --background
```

#### reinstall-tunnel-service

Update Cloudflared and reinstall its persistent service using the user's Cloudflare configuration. The command confirms before changing the service unless `--yes`, `-y` is passed.

```bash
devops network cloudflare reinstall-tunnel-service
```

#### add-ip-exclusion-to-warp

Add one or more IP exclusions to Cloudflare WARP, then reconnect WARP. `--ip`, `-i` is required and takes a comma-separated list; the command confirms unless `--yes`, `-y` is passed.

```bash
devops network cloudflare add-ip-exclusion-to-warp --ip 192.168.20.25,10.0.0.15
```

#### tunnel-status

Inspect Cloudflare Tunnel redundancy and connector state locally and over SSH.

```bash
devops network cloudflare tunnel-status TUNNEL_NAME [OPTIONS]
```

Key options:

| Option | Description |
|--------|-------------|
| `--host`, `-H` | SSH connector host; repeat for multiple hosts |
| `--hostname`, `-n` | Published hostname to verify on each connector |
| `--no-local`, `-l` | Exclude the local connector, which is included by default |
| `--cloudflared`, `-f` | Cloudflared executable path on each connector |
| `--config`, `-c` | Cloudflared configuration path on each connector |
| `--service`, `-s` | Systemd service name on each connector |
| `--json`, `-j` | Print tunnel health and connector records as JSON |

#### update-connectors

Update connectors sequentially, waiting for each service to become healthy before continuing.

```bash
devops network cloudflare update-connectors [OPTIONS]
```

Key options:

| Option | Description |
|--------|-------------|
| `--host`, `-H` | SSH connector host; repeat for a rolling update |
| `--no-local`, `-l` | Exclude the local connector, which is included by default |
| `--cloudflared`, `-f` | Cloudflared executable path on each connector |
| `--service`, `-s` | Systemd service name on each connector |
| `--timeout`, `-t` | Seconds to wait for each restarted service |
| `--yes`, `-y` | Run without confirmation |

#### sync-routes

Copy selected ingress routes from one connector configuration to another without copying tunnel credentials.

```bash
devops network cloudflare sync-routes --hostname HOSTNAME [OPTIONS]
```

Key options:

| Option | Description |
|--------|-------------|
| `--hostname`, `-n` | Source hostname route to copy; repeat as needed |
| `--source-host`, `-S` | SSH host containing the source configuration |
| `--source-config`, `-C` | Source Cloudflared configuration path |
| `--host`, `-H` | SSH target host; omit for the local machine |
| `--config`, `-c` | Target Cloudflared configuration path |
| `--cloudflared`, `-f` | Cloudflared executable path on the target |
| `--service`, `-s` | Target systemd service name |
| `--timeout`, `-t` | Seconds to wait for the restarted service |
| `--yes`, `-y` | Run without confirmation |

### device

Device-specific WiFi and WSL actions live under a nested Typer app:

```bash
devops network device [SUBCOMMAND] [ARGS]...
```

`devops network device --help` currently exposes:

| Command | Description |
|---------|-------------|
| `connect-wifi` | Connect to a configured or selected WiFi network |
| `bind-wsl-port` | Bind a WSL port onto the Windows host |
| `open-wsl-port` | Open Windows Firewall rules for WSL ports |
| `link-wsl-windows` | Link WSL home and Windows home directories |

#### connect-wifi

Connect to WiFi by SSID or by picking a scanned network. One of `--ssid`, `--interactive`, or `--list` is required.

```bash
devops network device connect-wifi [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--ssid`, `-n` | Exact SSID to connect to with a password source, or the name of a configured WiFi login when none is given |
| `--interactive`, `-i` | Pick a network interactively from the scanned list |
| `--list`, `-l` | Only list visible networks |
| `--password-file`, `-f` | Read the network password from a file; `-` reads stdin |
| `--password-env`, `-E` | Environment variable containing the network password |
| `--json`, `-j` | Print the network inventory or connection receipt as JSON |

Examples:

```bash
devops network device connect-wifi --list
devops network device connect-wifi --interactive
devops network device connect-wifi --ssid HomeNet --password-env WIFI_PASSWORD
```

#### bind-wsl-port

Bind a WSL port onto the Windows host using `netsh interface portproxy`. Run it inside WSL: it forwards the port on every Windows address (`0.0.0.0`) to the same port on the WSL IPv4 address, replacing an existing proxy for that port.

```bash
devops network device bind-wsl-port 8080
```

#### open-wsl-port

Create one inbound TCP allow rule in Windows Firewall, named `WSL Ports <ports>`, covering the listed ports and ranges. Run it on Windows itself, not inside WSL.

```bash
devops network device open-wsl-port 8080,3000-3005,443
```

#### link-wsl-windows

Create a symlink to the other side's home directory: inside WSL, `~/win` points to the Windows home; on Windows, `~\wsl` points to the WSL home. A link that already points elsewhere is replaced; any other existing path at that name is an error.

```bash
devops network device link-wsl-windows [OPTIONS]
```

Key option:

| Option | Description |
|--------|-------------|
| `--windows-username`, `-u` | Override the auto-detected Windows username (used inside WSL) |

### show-address

Show local interface addresses plus the public IP address when available. `--json`, `-j` prints the public, LAN, and interface addresses as JSON.

```bash
devops network show-address
```

### vscode-share

Generate or run VS Code Tunnel and `code serve-web` commands.

```bash
devops network vscode-share ACTION [OPTIONS]
```

Supported actions from current help:

- `run` (`r`)
- `install-service` (`i`)
- `uninstall-service` (`u`)
- `share-local` (`l`)
- `status` (`s`)

Key options from current help:

| Option | Description |
|--------|-------------|
| `--name`, `-n` | Tunnel or service name |
| `--path`, `-p` | Server base path for `share-local` |
| `--host`, `-H` | Host for `share-local` (default `0.0.0.0`) |
| `--directory`, `-d` | Folder to open in `share-local` mode; defaults to the current working directory |
| `--token`, `-t` | Connection token for `share-local`; defaults to a generated one |
| `--token-file`, `-f` | File holding the connection token for `share-local` |
| `--no-auth`, `-N` | Serve `share-local` without a connection token |
| `--cli-data-dir`, `-D` | VS Code CLI data directory used by every generated command |
| `--extra-args`, `-e` | Extra CLI arguments to append |
| `--background`, `-B` | Keep a `run` or `share-local` process running after it is ready |
| `--json`, `-j` | Print the service status or the ready URL, PID, and log file as JSON |
| `--timeout`, `-T` | Seconds to wait for command completion or readiness (default 60) |

Examples:

```bash
devops network vscode-share run --name labbox
devops network vscode-share install-service --name labbox
devops network vscode-share share-local --directory . --host 0.0.0.0
devops network vscode-share status
```

Before `run` or `install-service`, StackOps shows whether a VS Code tunnel credential is stored and whether its provider is GitHub or Microsoft. VS Code does not expose the credential's exact username or email. To guarantee which account is used, run `code tunnel user logout`, then `code tunnel user login --provider github` or `code tunnel user login --provider microsoft` before starting the tunnel.

---
