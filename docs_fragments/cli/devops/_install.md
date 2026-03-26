## install

The primary package installation command. Supports single packages, multiple packages, package groups, and interactive selection.

```bash
devops install [OPTIONS] [WHICH]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `WHICH` | Comma-separated list of package names, group name, or GitHub/binary URL |

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--group` | `-g` | Treat `WHICH` as a package group name |
| `--interactive` | `-i` | Interactive selection with TV/fzf interface |

### Installation Modes

#### Single Package

```bash
# Install a single package by name
devops install btop
devops install fd
devops install yazi
```

#### Multiple Packages

```bash
# Install multiple packages (comma-separated, no spaces)
devops install btop,fd,bat,rg,fzf

# With spaces (use quotes)
devops install "btop, fd, bat, rg"
```

#### Package Groups

Install predefined bundles of related packages:

```bash
# Install terminal essentials (40+ tools)
devops install termabc --group
devops install termabc -g

# Install AI coding assistants
devops install agents -g

# Install full development environment
devops install dev -g

# Install system monitors
devops install sys-monitor -g
```

#### Interactive Mode

Launch an interactive selector with all available packages:

```bash
devops install --interactive
devops install -i
```

Features:
- Shows installation status (`✅` installed, `❌` not installed)
- Package descriptions displayed
- Multi-select supported
- Package groups prefixed with `📦`

#### From GitHub URL

Install directly from a GitHub repository:

```bash
# The installer will show available release assets for selection
devops install https://github.com/sharkdp/fd
devops install https://github.com/BurntSushi/ripgrep
```

#### From Binary URL

Install from a direct download URL:

```bash
devops install https://example.com/tool-v1.0-linux-amd64.tar.gz
```

### Available Package Groups

| Group | Description | Contents |
|-------|-------------|----------|
| `sysabc` | System essentials | Package managers, build tools, bun |
| `termabc` | Terminal power tools | 60+ CLI tools (search, monitors, shell) |
| `gui` | GUI applications | brave, code, git |
| `dev` | Full dev environment | 80+ tools across all categories |
| `dev-utils` | Development utilities | devcontainer, rust-analyzer, evcxr, geckodriver |
| `term-eye-candy` | Terminal visuals | lolcatjs, figlet-cli, boxes, cowsay |
| `agents` | AI assistants | aider, aichat, copilot, gemini, opencode-ai, mods, q, ... |
| `terminal-emulator` | Terminal emulators | Alacritty, Wezterm, warp, vtm, nushell |
| `shell` | Shell enhancements | zellij, mprocs, mcfly, atuin, starship |
| `browsers` | Web browsers | Brave, browsh, carbonyl |
| `code-editors` | Code editors | code, Cursor, lvim |
| `code-analysis` | Code & Git tools | lazygit, gitui, delta, gh, tokei, hyperfine |
| `db` | Database tools | SqliteBrowser, duckdb, DBeaver, rainfrog |
| `media` | Media players | ytui-music, termusic |
| `file-sharing` | File sharing | ngrok, cloudflared, ffsend, syncthing, rclone |
| `productivity` | Productivity | espanso, bitwarden, glow, gum, pandoc |
| `sys-monitor` | System monitors | btop, btm, procs, bandwhich, fastfetch |
| `search` | Search & file tools | fd, fzf, rg, bat, yazi, zoxide, dust |

### Listing Available Groups

```bash
# Show all available groups with their packages
devops install -g

# Output shows:
# 📦 sysabc              --   sysabc
# 📦 termabc             --   nano|lazygit|onefetch|...
# 📦 agents              --   aider|aichat|copilot|...
```

### Examples

```bash
# Essential terminal setup (recommended first install)
devops install sysabc -g && devops install termabc -g

# Install all AI coding assistants
devops install agents -g

# Selective installation
devops install btop,fd,rg,fzf,bat,zoxide,yazi

# Interactive browse and install
devops install -i

# Install from specific GitHub repo
devops install https://github.com/jesseduffield/lazygit
```

---
