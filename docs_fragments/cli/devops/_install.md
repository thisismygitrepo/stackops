## software

Install software and manage its catalog. The group provides `install`, `uninstall`, `explore`, `check`, `list`, `report`, `update-attrs`, `path`, `init`, `edit`, and `validate`. Installation supports single packages, multiple packages, package groups, and interactive selection.

```bash
devops software install [OPTIONS] [WHICH]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `WHICH` | Comma-separated package names, group names with `--group`, or a GitHub/binary URL |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--group` | `-g` | Treat `WHICH` as package group names |
| `--source` | `-s` | Catalog to use: `library`, `user`, or `all` (default); user entries override matching library names |
| `--custom-path` | `-p` | Use another user catalog file with `--source user` or `all` |
| `--interactive` | `-i` | Interactive selection with the `tv` picker |
| `--update` | `-u` | Reinstall or upgrade when supported |
| `--version` | `-v` | Specific version or tag to install when supported |

### Installation Modes

#### Single Package

```bash
# Install a single package by name
devops software install btop
devops software install fd
devops software install yazi
```

#### Multiple Packages

```bash
# Install multiple packages (comma-separated, no spaces)
devops software install btop,fd,bat,rg,fzf

# With spaces (use quotes)
devops software install "btop, fd, bat, rg"
```

#### Package Groups

Install predefined bundles of related packages:

```bash
# Install terminal essentials (48 tools)
devops software install termabc --group
devops software install termabc -g

# Install AI coding assistants
devops software install agents -g

# Install full development environment
devops software install dev -g

# Install several groups as one batch
devops software install sys-monitor,nw -g
```

#### Interactive Mode

Launch an interactive selector with all available packages:

```bash
devops software install --interactive
devops software install -i
```

Features:
- Shows installation status (`✅` installed, `❌` not installed)
- Package descriptions displayed
- Multi-select supported
- Package groups prefixed with `📦`

#### Explore by Category Labels

Browse installers by the `categoryLabels` stored in `installer_data.yaml`, then choose matching installers:

```bash
devops software explore
devops software explore ai-agents-assistants
```

#### From GitHub URL

Install directly from a GitHub repository:

```bash
# The installer will show available release assets for selection
devops software install https://github.com/sharkdp/fd
devops software install https://github.com/BurntSushi/ripgrep
```

#### From Binary URL

Install from a direct download URL:

```bash
devops software install https://example.com/tool-v1.0-linux-amd64.tar.gz
```

### Available Package Groups

| Group | Description | Contents |
|-------|-------------|----------|
| `sysabc` | System essentials | The single `sysabc` installer: base system packages through the existing package manager on Linux, Homebrew on macOS, winget plus PowerShell, Windows Terminal and Git on Windows; bun on all three |
| `termabc` | Terminal power tools | 48 tools: `search` + `shell` + `code-analysis` + `sys-monitor` |
| `search` | Search & file tools | 21 tools: yazi, fd, fzf, tv, rg, bat, zoxide, dust, ... |
| `shell` | Shell enhancements | nerdfont, tuios, mcfly, starship |
| `code-analysis` | Code & Git tools | 16 tools: lazygit, gitui, delta, gh, tokei, hyperfine, jq, ... |
| `sys-monitor` | System monitors | btop, btm, ntop, procs, cpufetch, fastfetch, pstop |
| `dev` | Full dev environment | 92 entries: `terminal` + `browsers` + `editors` + `db-all` + `media` + `file-sharing` + `dev-utils` + `code-analysis` + `productivity` + `eye` |
| `dev-utils` | Development utilities | devcontainer, rust-analyzer, evcxr, geckodriver, git, m365 |
| `eye` | Terminal visuals | lolcatjs, figlet-cli, boxes, cowsay |
| `agents` | AI assistants | 36 entries: aider, aichat, copilot, antigravity, crush, mods, q, pi, ... |
| `terminal` | Terminal emulators & shells | alacritty, ghostty, wezterm, warp-terminal, vtm, edex-ui, extraterm, nu |
| `browsers` | Web browsers | brave, bypass-paywalls-chrome, browsh, carbonyl |
| `editors` | Code editors | code, hx, zed |
| `db-all` | All database tools | 15 entries: `db-tui` + `db-cli` + `db-desktop` + `db-web` |
| `db-cli` | Database CLIs | dolt, duckdb, postgresql-client, sqlite3, redis-cli |
| `db-desktop` | Database desktop apps | dbgate, dbeaver, sqliteBrowser |
| `db-web` | Database web UIs | pgweb |
| `db-tui` | Database TUIs | rainfrog, lazysql, dblab, usql, harlequin, sqlit |
| `media` | Media players & tools | ytui-music, youtube-tui, termusic, rmpc, kronos, OBS Background removal |
| `gui` | GUI applications | brave, chatgpt, wezterm |
| `nw` | Network tools | bandwhich, psnet, ipinfo, sniffnet, topgrade, speedtest, rclone |
| `file-sharing` | File sharing & sync | 18 entries: ngrok, cloudflared, ffsend, syncthing, restic, ... |
| `productivity` | Productivity | 12 entries: espanso, glow, gum, pandoc, marp, ... |

Counts are the names each group lists. A listed name is skipped when the selected catalog has no installer for it on the current OS and architecture.

### Listing Available Groups

```bash
# --group without a group name reports the missing name, then prints
# a table of every group (Group, AppsBundled) and exits with an error
devops software install -g
```

The interactive picker (`devops software install -i`) also lists the groups, prefixed with `📦`.

### Examples

```bash
# Essential terminal setup (recommended first install)
devops software install sysabc -g && devops software install termabc -g

# Install all AI coding assistants
devops software install agents -g

# Selective installation
devops software install btop,fd,rg,fzf,bat,zoxide,yazi

# Interactive browse and install
devops software install -i

# Install from specific GitHub repo
devops software install https://github.com/jesseduffield/lazygit
```

### Other software commands

| Command | Description |
|---------|-------------|
| `uninstall WHICH` | Remove apps: delete the program file StackOps installed, or run the package manager's uninstall command |
| `check WHICH` | Report whether executables are installed, without installing; `--group` takes one check group (currently only `agents`), not an install group |
| `list [QUERY]` | List catalog definitions, filtered by name, description, or category; `--json` prints full definitions |
| `report` | Rank entries by their saved GitHub commit dates; `--reverse` shows newest first |
| `update-attrs` | Refresh the saved GitHub commit dates of the library or user catalog |
| `path` | Print catalog, schema, and installer-script paths as JSON |
| `init` / `edit` / `validate` | Create, edit, or validate the user catalog |

---
