## self

Self management commands.

```bash
devops self [SUBCOMMAND] [ARGS]...
```

Manage machineconfig itself: updates, configuration, docs preview, and CLI exploration.

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
