# devops

DevOps operations, package management, and system administration.

---

## Usage

```bash
devops [OPTIONS] COMMAND [ARGS]...
```

---

## Commands Overview

| Command | Shortcut | Description |
|---------|----------|-------------|
| `install` | `i` | Install packages and package groups |
| `repos` | `r` | Manage development repositories |
| `config` | `c` | Configuration management |
| `data` | `d` | Data management |
| `self` | `s` | Self management |
| `network` | `n` | Network management |
| `execute` | `e` | Execute scripts |

---

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
- Shows installation status (✅ installed, ❌ not installed)
- Package descriptions displayed
- Multi-select supported
- Package groups prefixed with 📦

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

## repos

Manage development repositories.

```bash
devops repos [SUBCOMMAND] [ARGS]...
```

Handles cloning, updating, and managing development repositories.

---

## config

Configuration management.

```bash
devops config [SUBCOMMAND] [ARGS]...
```

Manage dotfiles, packaged assets, example config generation, and terminal profile/theme setup.

Current `devops config --help` exposes:

| Command | Description |
|---------|-------------|
| `sync` | Apply dotfile mappings with `symlink` or `copy` |
| `register` | Register a file or directory into the user mapper |
| `edit` | Open the library or user `mapper.toml` |
| `export-dotfiles` | Export `~/dotfiles` for machine migration |
| `import-dotfiles` | Import an exported dotfiles archive |
| `copy-assets` | Copy packaged scripts and settings onto the machine |
| `dump` | Write example configuration files such as `.ve.example.yaml` |
| `terminal` | Shell profile and terminal theme commands |

### sync

Apply the current dotfile mapping set.

```bash
devops config sync --sensitivity <public|private|all> --method <symlink|copy> [OPTIONS]
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--sensitivity`, `-s` | Required. Choose `private`, `public`, or `all` |
| `--method`, `-m` | Required. Use `symlink` or `copy` |
| `--repo`, `-r` | Select mappings from `library`, `user`, or `all` |
| `--on-conflict`, `-o` | Conflict policy such as `throw-error`, `overwrite-self-managed`, or `overwrite-default-path` |
| `--which`, `-w` | Limit the run to specific mapping names, or use `all` |

If `--which` is omitted, the command falls back to interactive selection.

Examples:

```bash
# Sync all public mappings with symlinks
devops config sync --sensitivity public --method symlink --which all

# Apply only user-defined private mappings by copying files
devops config sync --sensitivity private --method copy --repo user
```

### register

Register a new config file or directory into the self-managed dotfiles area and, by default, record that mapping in the user mapper.

```bash
devops config register [OPTIONS] FILE
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--method`, `-m` | Store it with `copy` or `symlink` semantics |
| `--on-conflict`, `-o` | Conflict strategy during the initial transfer |
| `--sensitivity`, `-s` | Mark the mapping as `private` or `public` |
| `--destination`, `-d` | Override the default self-managed destination |
| `--section`, `-se` | Section name to write inside the user mapper |
| `--os` | Restrict the mapping to one OS or a comma-separated list |
| `--shared`, `-sh` | Place the managed file under a shared destination layout |
| `--record`, `-r` | Record the mapping in the user mapper file |

Examples:

```bash
# Register a private file and record it in the default mapper section
devops config register ~/.config/htop/htoprc --sensitivity private

# Register a public directory with symlink semantics
devops config register ~/.config/nvim --method symlink --sensitivity public --section editors
```

### edit

Open the dotfile mapper in `nano`, `hx`, or `code`.

```bash
devops config edit --editor hx --repo user
```

The user mapper is created automatically if it does not exist yet.

### export-dotfiles

Package and encrypt `~/dotfiles` for transfer to another machine.

```bash
devops config export-dotfiles <password>
```

Optional transfer flags:

| Option | Description |
|--------|-------------|
| `--over-internet`, `-i` | Internet-transfer flag present in the CLI, but the current implementation is not finished |
| `--over-ssh`, `-s` | Use SSH/SCP-style transfer |

### import-dotfiles

Import an encrypted dotfiles archive from a local path or URL.

```bash
devops config import-dotfiles --url /path/to/dotfiles.zip.enc --pwd <password>
```

### copy-assets

Copy packaged helper assets from the library onto the current machine.

```bash
devops config copy-assets <scripts|settings|both>
```

Examples:

```bash
devops config copy-assets scripts
devops config copy-assets both
```

### dump

Write example configuration files into the current directory.

```bash
devops config dump --which ve
```

At the moment, `ve` writes `.ve.example.yaml` in the current working directory.

### terminal

Terminal setup lives under a nested Typer app:

```bash
devops config terminal [SUBCOMMAND] [ARGS]...
```

`devops config terminal --help` currently exposes:

| Command | Description |
|---------|-------------|
| `config-shell` | Create or configure the default shell profile or Nushell profile |
| `starship-theme` | Interactive Starship prompt theme selection |
| `pwsh-theme` | Interactive PowerShell prompt theme selection |
| `wezterm-theme` | Interactive WezTerm theme selection |
| `ghostty-theme` | Interactive Ghostty theme selection |
| `windows-terminal-theme` | Interactive Windows Terminal color scheme selection |

The nested help screens render `Usage: devops terminal ...`, but the full entrypoint remains `devops config terminal ...`.

Examples:

```bash
devops config terminal config-shell --which default
devops config terminal config-shell --which nushell
devops config terminal wezterm-theme
devops config terminal ghostty-theme
```

---

## data

Data backup and retrieval operations.

```bash
devops data [SUBCOMMAND] [ARGS]...
```

Back up configured files and directories to cloud storage, retrieve them back, and maintain the backup item registry.

Current `devops data --help` exposes:

| Command | Description |
|---------|-------------|
| `sync` | Generate backup or retrieve commands through `cloud copy` |
| `register` | Add or update a backup entry in the user data-mapping file |
| `edit` | Open the user or library backup configuration file |

### sync

Generate backup or restore commands for registered items.

```bash
devops data sync <up|down> [OPTIONS]
```

`up` means backup to the cloud. `down` means retrieve from the cloud.

Key options from current help:

| Option | Description |
|--------|-------------|
| `--cloud`, `-c` | Select the rclone config name to use |
| `--which`, `-w` | Choose specific items, a whole group, or `all` |
| `--repo`, `-r` | Load backup entries from `library`, `user`, or `all` |

If `--which` is omitted, the command falls back to interactive selection. The selector accepts:

- a group name such as `dotfiles`
- a specific item such as `dotfiles.bashrc`
- `all` for every applicable entry

Examples:

```bash
# Generate commands to back up every registered item
devops data sync up --which all

# Generate commands to restore one group from the user backup config
devops data sync down --repo user --which dotfiles

# Generate commands for selected entries with a specific cloud config
devops data sync up --cloud myremote --which dotfiles.bashrc,history.shell
```

`devops data sync` filters entries by the current OS and then prints the generated `cloud copy` script based on each item's `os`, `zip`, `encrypt`, and `rel2home` fields.

### register

Add or update one entry inside the user backup configuration file at `~/dotfiles/machineconfig/mapper_data.toml`.

```bash
devops data register [OPTIONS] PATH_LOCAL
```

Key options from current help:

| Option | Description |
|--------|-------------|
| `--group`, `-g` | Target group/table name inside the config file |
| `--name`, `-n` | Override the generated entry name |
| `--path-cloud`, `-C` | Override the remote path; omit it to let machineconfig deduce one |
| `--zip`, `-z` | Zip before upload |
| `--encrypt`, `-e` | Encrypt before upload |
| `--rel2home`, `-r` | Store the local path relative to your home directory |
| `--os`, `-o` | Restrict the entry to `linux`, `darwin`, `windows`, or a comma-separated list |

Examples:

```bash
# Register a config directory for encrypted, zipped backup
devops data register ~/.config/wezterm --group dotfiles --zip --encrypt

# Register a directory with an explicit cloud path
devops data register ~/Documents/work --group documents --path-cloud backups/work --os linux,darwin
```

If `--name` is omitted, the command generates one from the local path and OS filter.

### edit

Open the backup configuration file in `nano`, `hx`, or `code`.

```bash
devops data edit --editor hx --repo user
```

The user backup config is created automatically if it does not exist yet.

### Backup File Layout

The user backup file uses grouped TOML tables. A representative entry looks like this:

```toml
[dotfiles]
wezterm = { path_local = "~/.config/wezterm", path_cloud = "^", encrypt = true, zip = true, rel2home = true, os = "linux,darwin" }
```

Selection behavior for `devops data sync --which ...`:

- `dotfiles` selects the whole group
- `dotfiles.wezterm` selects one item
- `all` selects every applicable item

The nested help screens render `Usage: devops sync ...`, `devops register ...`, and `devops edit ...`, but the full entrypoints remain `devops data sync ...`, `devops data register ...`, and `devops data edit ...`.

---

## self

Self management commands.

```bash
devops self [SUBCOMMAND] [ARGS]...
```

Manage machineconfig itself - updates, configuration, etc.

Current `devops self --help` exposes:

| Command | Description |
|---------|-------------|
| `update` | Upgrade machineconfig |
| `init` | Print or run init scripts |
| `status` | Inspect the current machine configuration state |
| `install` | Install machineconfig locally or run the interactive setup path |
| `explore` | Inspect the CLI graph |
| `readme` | Render the project README in the terminal |

When `~/code/machineconfig` exists, `devops self` also exposes checkout-oriented commands:

| Command | Description |
|---------|-------------|
| `buid-docker` | Build Docker images from the repo scripts |
| `security` | Run security-related CLI tools |
| `docs` | Serve the local docs preview, optionally with `--rebuild` |

### explore

Current self-management commands also expose the CLI graph explorer through `devops self explore`.

=== "Overview"

    ```bash
    devops self explore --help

    Usage: devops [OPTIONS] COMMAND [ARGS]...

    🧭 <g> Visualize the MachineConfig CLI graph in multiple formats.

    Commands:
      search    🔎 <s> Search all cli_graph.json command entries.
      tree      🌳 <t> Render a rich tree view in the terminal.
      dot       🧩 <d> Export the graph as Graphviz DOT.
      sunburst  ☀ <b> Render a Plotly sunburst view.
      treemap   🧱 <m> Render a Plotly treemap view.
      icicle    🧊 <i> Render a Plotly icicle view.
      tui       📚 <u> NAVIGATE command structure with TUI
    ```

=== "Hierarchy"

    `devops self explore` dispatches to a nested Typer app. The nested help screens render `Usage: devops ...`, but the entrypoint remains `devops self explore ...`.

    ```text
    devops self explore
    ├── search
    ├── tree
    ├── dot
    ├── sunburst
    ├── treemap
    ├── icicle
    └── tui
    ```

    #### `search`

    ```bash
    devops self explore search
    ```

    Interactive fuzzy-search over `src/machineconfig/scripts/python/graph/cli_graph.json`, followed by the full selected entry. Representative result excerpt:

    ```json
    {
      "kind": "command",
      "name": "tree",
      "help": "🌳 <t> Render a rich tree view in the terminal.",
      "source": {
        "file": "src/machineconfig/scripts/python/graph/visualize/cli_graph_app.py",
        "module": "machineconfig.scripts.python.graph.visualize.cli_graph_app",
        "callable": "tree"
      }
    }
    ```

    #### `tree`

    ```bash
    devops self explore tree --max-depth 2
    ```

    Representative output:

    ```text
    mcfg - MachineConfig CLI - Manage your machine configurations and workflows
    ├── devops - 🔧 DevOps operations
    │   ├── install - 🔧 <i> Install essential packages
    │   ├── repos - 📁 <r> Manage development repositories
    │   ├── config - 🧰 <c> configuration subcommands
    │   ├── data - 🗄 <d> Backup and retrieve configuration files and directories to/from cloud storage using rclone.
    │   ├── self - 🔄 <s> self operations subcommands
    │   ├── network - 🔐 <n> Network subcommands
    │   └── execute - 🚀 <e> Execute python/shell scripts from pre-defined directories or as command
    ├── cloud - ☁ Cloud management commands
    ├── sessions - Layouts management subcommands
    ├── agents - 🤖 AI Agents management subcommands
    ├── utils - ⚙ utilities operations
    ├── fire - <f> Fire and manage jobs
    └── croshell - <r> Cross-shell command execution
    ```

    #### `dot`

    ```bash
    devops self explore dot --max-depth 2
    ```

    Representative output:

    ```dot
    digraph cli_graph {
      graph [rankdir=LR, splines=true, bgcolor="white"];
      node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, color="#333333"];
      edge [color="#999999"];
      "mcfg" [label="mcfg\nMachineConfig CLI - Manage your machine configurations and workflows", shape="doubleoctagon", fillcolor="#f1f1f1", color="#555555"];
      "mcfg devops" [label="devops\n🔧 DevOps operations", shape="box", fillcolor="#dbeafe", color="#2563eb"];
      "mcfg" -> "mcfg devops";
      "mcfg devops self" [label="self\n🔄 <s> self operations subcommands", shape="box", fillcolor="#dbeafe", color="#2563eb"];
      "mcfg devops" -> "mcfg devops self";
    }
    ```

    #### `sunburst`

    ```bash
    devops self explore sunburst --output ./sunburst.html
    ```

    Interactive HTML result: [sunburst.html](../assets/devops-self-explore/sunburst.html)

    #### `treemap`

    ```bash
    devops self explore treemap --output ./treemap.html
    ```

    Interactive HTML result: [treemap.html](../assets/devops-self-explore/treemap.html)

    #### `icicle`

    ```bash
    devops self explore icicle --output ./icicle.html
    ```

    Interactive HTML result: [icicle.html](../assets/devops-self-explore/icicle.html)

    #### `tui`

    ```bash
    devops self explore tui
    ```

    Launches the full-screen Textual navigator with:

    - `/` to focus search
    - `c` to copy the selected command
    - `r` to run the selected command
    - `b` to build a command with arguments
    - `?` to open the in-app help
    - `q` to quit

=== "Outcome Previews"

    Static previews below were generated from the current repo. The Plotly views use `--output ...html` here so the docs can embed the live charts inline.

    #### `search`

    ```bash
    devops self explore search
    ```

    `search` is interactive, so the exact result depends on the selected entry. Choosing `tree` currently shows:

    ```json
    {
      "kind": "command",
      "name": "tree",
      "help": "🌳 <t> Render a rich tree view in the terminal.",
      "source": {
        "file": "src/machineconfig/scripts/python/graph/visualize/cli_graph_app.py",
        "module": "machineconfig.scripts.python.graph.visualize.cli_graph_app",
        "callable": "tree"
      }
    }
    ```

    #### `tree`

    ```bash
    devops self explore tree --max-depth 2
    ```

    ```text
    mcfg - MachineConfig CLI - Manage your machine configurations and workflows
    ├── devops - 🔧 DevOps operations
    │   ├── install - 🔧 <i> Install essential packages
    │   ├── repos - 📁 <r> Manage development repositories
    │   ├── config - 🧰 <c> configuration subcommands
    │   ├── data - 🗄 <d> Backup and retrieve configuration files and directories to/from cloud storage using rclone.
    │   ├── self - 🔄 <s> self operations subcommands
    │   ├── network - 🔐 <n> Network subcommands
    │   └── execute - 🚀 <e> Execute python/shell scripts from pre-defined directories or as command
    ├── cloud - ☁ Cloud management commands
    ├── sessions - Layouts management subcommands
    ├── agents - 🤖 AI Agents management subcommands
    ├── utils - ⚙ utilities operations
    ├── fire - <f> Fire and manage jobs
    └── croshell - <r> Cross-shell command execution
    ```

    #### `dot`

    ```bash
    devops self explore dot --max-depth 2
    ```

    ```dot
    digraph cli_graph {
      graph [rankdir=LR, splines=true, bgcolor="white"];
      node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, color="#333333"];
      edge [color="#999999"];
      "mcfg" [label="mcfg\nMachineConfig CLI - Manage your machine configurations and workflows", shape="doubleoctagon", fillcolor="#f1f1f1", color="#555555"];
      "mcfg devops" [label="devops\n🔧 DevOps operations", shape="box", fillcolor="#dbeafe", color="#2563eb"];
      "mcfg" -> "mcfg devops";
      "mcfg devops self" [label="self\n🔄 <s> self operations subcommands", shape="box", fillcolor="#dbeafe", color="#2563eb"];
      "mcfg devops" -> "mcfg devops self";
    }
    ```

    #### `sunburst`

    ```bash
    devops self explore sunburst --output docs/assets/devops-self-explore/sunburst.html --template plotly_dark
    ```

    <iframe
      class="plotly-preview-frame"
      src="../assets/devops-self-explore/sunburst.html"
      title="Interactive sunburst preview"
      loading="lazy"
    ></iframe>

    Standalone HTML result: [sunburst.html](../assets/devops-self-explore/sunburst.html)

    #### `treemap`

    ```bash
    devops self explore treemap --output docs/assets/devops-self-explore/treemap.html --template plotly_dark
    ```

    <iframe
      class="plotly-preview-frame"
      src="../assets/devops-self-explore/treemap.html"
      title="Interactive treemap preview"
      loading="lazy"
    ></iframe>

    Standalone HTML result: [treemap.html](../assets/devops-self-explore/treemap.html)

    #### `icicle`

    ```bash
    devops self explore icicle --output docs/assets/devops-self-explore/icicle.html --template plotly_dark
    ```

    <iframe
      class="plotly-preview-frame"
      src="../assets/devops-self-explore/icicle.html"
      title="Interactive icicle preview"
      loading="lazy"
    ></iframe>

    Standalone HTML result: [icicle.html](../assets/devops-self-explore/icicle.html)

    #### `tui`

    ```bash
    devops self explore tui
    ```

    ![TUI preview](../assets/devops-self-explore/tui.svg){ width="100%" }

    `tui` launches the full-screen navigator shown above. The live app then lets you search, inspect command details, copy a command, run it, or build one with arguments.

---

## network

Network management.

```bash
devops network [SUBCOMMAND] [ARGS]...
```

Network configuration and diagnostics.

---

## execute

Execute Python or shell scripts from pre-defined directories.

```bash
devops execute [OPTIONS] [NAME]
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `--where` | `-w` | Script location: `all`, `private`, `public`, `library`, `dynamic`, `custom` |
| `--interactive` | `-i` | Interactive selection of scripts |
| `--command` | `-c` | Run as command |
| `--list` | `-l` | List available scripts |

### Examples

```bash
# Run a script by name
devops execute my_script

# List all available scripts
devops execute --list
devops e -l

# Interactive script selection
devops execute --interactive
devops e -i

# Run from specific location
devops execute my_script --where private
```

---

## Quick Reference

```bash
# === Package Installation ===
devops i btop                    # Install single package
devops i btop,fd,bat             # Install multiple packages
devops i termabc -g              # Install package group
devops i -i                      # Interactive mode
devops i https://github.com/...  # From GitHub

# === Group Installation (Recommended Order) ===
devops i sysabc -g               # 1. System essentials
devops i termabc -g              # 2. Terminal tools
devops i agents -g               # 3. AI assistants (optional)

# === Script Execution ===
devops e -l                      # List scripts
devops e my_script               # Run script
devops e -i                      # Interactive

# === Help ===
devops --help
devops install --help
```

---

## Platform Support

| Feature | Linux | macOS | Windows |
|---------|-------|-------|---------|
| Package Manager Install | `apt`, `nala`, `snap` | `brew` | `winget`, `scoop` |
| GitHub Release Install | ✅ | ✅ | ✅ |
| Custom Python Installers | ✅ | ✅ | ✅ |
| Shell Script Installers | ✅ | ✅ | ❌ |
| PowerShell Installers | ❌ | ❌ | ✅ |
| Binary Path | `~/.local/bin` | `/usr/local/bin` | `%LOCALAPPDATA%\Microsoft\WindowsApps` |

---

## See Also

- [Installer Module API](../api/jobs/installer.md) - Detailed API documentation
- [Package Groups](../api/jobs/installer.md#package-groups) - Full package group contents
- [Custom Installers](../api/jobs/installer.md#custom-python-installers) - Creating custom installers
