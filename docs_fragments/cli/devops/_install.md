## software

Install software and manage its catalog. The group provides `install`, `list`, `path`, `init`, `edit`, and `validate`. Installation supports single packages, multiple packages, package groups, and interactive selection.

```bash
devops software install [OPTIONS] [WHICH]
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
| `--explore` | `-x` | Explore installer `categoryLabels`, then choose matching installers |
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
# Install terminal essentials (40+ tools)
devops software install termabc --group
devops software install termabc -g

# Install AI coding assistants
devops software install agents -g

# Install full development environment
devops software install dev -g

# Install system monitors
devops software install sys-monitor -g
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

Browse installers by the `categoryLabels` stored in `installer_data.json`, then choose matching installers:

```bash
devops software install --explore
devops software install -x
devops software install ai-agents-assistants -x
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
| `sysabc` | System essentials | Package managers, build tools, bun |
| `termabc` | Terminal power tools | 60+ CLI tools (search, monitors, shell) |
| `gui` | GUI applications | brave, code, git |
| `dev` | Full dev environment | 80+ tools across all categories |
| `dev-utils` | Development utilities | devcontainer, rust-analyzer, evcxr, geckodriver |
| `term-eye-candy` | Terminal visuals | lolcatjs, figlet-cli, boxes, cowsay |
| `agents` | AI assistants | aider, aichat, copilot, antigravity/agy, opencode-ai, mods, q, ... |
| `terminal-emulator` | Terminal emulators | Alacritty, Wezterm, warp, vtm, nushell |
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
devops software install -g

# Output shows:
# 📦 sysabc              --   sysabc
# 📦 termabc             --   nano|lazygit|onefetch|...
# 📦 agents              --   aider|aichat|copilot|...
```

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

---
