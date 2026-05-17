from typing import TypedDict


EmptySubcommands = TypedDict("EmptySubcommands", {})


class LeafCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: EmptySubcommands


DevopsReposSubcommands = TypedDict(
    "DevopsReposSubcommands",
    {
        "sync": LeafCommand,
        "register": LeafCommand,
        "checkout-to-commit": LeafCommand,
        "checkout-to-branch": LeafCommand,
        "action": LeafCommand,
        "analyze": LeafCommand,
        "guard": LeafCommand,
        "viz": LeafCommand,
        "count-lines": LeafCommand,
        "config-linters": LeafCommand,
        "cleanup": LeafCommand,
    },
)

DevopsConfigTerminalSubcommands = TypedDict(
    "DevopsConfigTerminalSubcommands",
    {
        "config-shell": LeafCommand,
        "starship-theme": LeafCommand,
        "pwsh-theme": LeafCommand,
        "wezterm-theme": LeafCommand,
        "ghostty-theme": LeafCommand,
        "windows-terminal-theme": LeafCommand,
    },
)

DevopsDataSubcommands = TypedDict(
    "DevopsDataSubcommands",
    {
        "sync": LeafCommand,
        "register": LeafCommand,
        "edit": LeafCommand,
    },
)

DevopsSelfSecuritySubcommands = TypedDict(
    "DevopsSelfSecuritySubcommands",
    {
        "scan": LeafCommand,
        "list": LeafCommand,
        "upload": LeafCommand,
        "download": LeafCommand,
        "install": LeafCommand,
        "report": LeafCommand,
    },
)

DevopsSelfExploreSubcommands = TypedDict(
    "DevopsSelfExploreSubcommands",
    {
        "search": LeafCommand,
        "tree": LeafCommand,
        "dot": LeafCommand,
        "view": LeafCommand,
        "tui": LeafCommand,
    },
)

DevopsSelfBuildAssetsSubcommands = TypedDict(
    "DevopsSelfBuildAssetsSubcommands",
    {
        "update-cli-graph": LeafCommand,
        "regenerate-charts": LeafCommand,
    },
)

DevopsSelfWorkflowsSubcommands = TypedDict(
    "DevopsSelfWorkflowsSubcommands",
    {
        "update-installer": LeafCommand,
        "update-test": LeafCommand,
        "update-docs": LeafCommand,
        "update-logic": LeafCommand,
    },
)

DevopsNetworkSshSubcommands = TypedDict(
    "DevopsNetworkSshSubcommands",
    {
        "install-server": LeafCommand,
        "change-port": LeafCommand,
        "add-key": LeafCommand,
        "debug": LeafCommand,
    },
)

DevopsNetworkDeviceSubcommands = TypedDict(
    "DevopsNetworkDeviceSubcommands",
    {
        "switch-public-ip": LeafCommand,
        "wifi-select": LeafCommand,
        "bind-wsl-port": LeafCommand,
        "open-wsl-port": LeafCommand,
        "link-wsl-windows": LeafCommand,
        "reset-cloudflare-tunnel": LeafCommand,
        "add-ip-exclusion-to-warp": LeafCommand,
    },
)

CloudSubcommands = TypedDict(
    "CloudSubcommands",
    {
        "sync": LeafCommand,
        "copy": LeafCommand,
        "mount": LeafCommand,
        "ftpx": LeafCommand,
    },
)

TerminalSubcommands = TypedDict(
    "TerminalSubcommands",
    {
        "run": LeafCommand,
        "run-all": LeafCommand,
        "run-aoe": LeafCommand,
        "attach": LeafCommand,
        "kill": LeafCommand,
        "trace": LeafCommand,
        "create-from-function": LeafCommand,
        "balance-load": LeafCommand,
        "create-template": LeafCommand,
        "summarize": LeafCommand,
    },
)

AgentsParallelSubcommands = TypedDict(
    "AgentsParallelSubcommands",
    {
        "create": LeafCommand,
        "create-context": LeafCommand,
        "run-parallel": LeafCommand,
        "collect": LeafCommand,
        "make-template": LeafCommand,
    },
)

AgentsBrowserSubcommands = TypedDict(
    "AgentsBrowserSubcommands",
    {
        "install-tech": LeafCommand,
        "launch-browser": LeafCommand,
    },
)

UtilsMachineSubcommands = TypedDict(
    "UtilsMachineSubcommands",
    {
        "kill-process": LeafCommand,
        "environment": LeafCommand,
        "get-machine-specs": LeafCommand,
        "list-devices": LeafCommand,
        "mount": LeafCommand,
    },
)

UtilsPyprojectSubcommands = TypedDict(
    "UtilsPyprojectSubcommands",
    {
        "init-project": LeafCommand,
        "upgrade-packages": LeafCommand,
        "type-hint": LeafCommand,
        "type-check": LeafCommand,
        "type-fix": LeafCommand,
        "test-runtime": LeafCommand,
        "test-reference": LeafCommand,
    },
)

UtilsFileSubcommands = TypedDict(
    "UtilsFileSubcommands",
    {
        "edit": LeafCommand,
        "download": LeafCommand,
        "pdf-merge": LeafCommand,
        "pdf-compress": LeafCommand,
        "read-db": LeafCommand,
    },
)

SeekSubcommands = TypedDict(
    "SeekSubcommands",
    {
        "seek": LeafCommand,
    },
)


class DevopsReposCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsReposSubcommands


class DevopsConfigTerminalCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsConfigTerminalSubcommands


class DevopsDataCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsDataSubcommands


class DevopsSelfSecurityCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsSelfSecuritySubcommands


class DevopsSelfExploreCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsSelfExploreSubcommands


class DevopsSelfBuildAssetsCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsSelfBuildAssetsSubcommands


class DevopsSelfWorkflowsCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsSelfWorkflowsSubcommands


class DevopsNetworkSshCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsNetworkSshSubcommands


class DevopsNetworkDeviceCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsNetworkDeviceSubcommands


class CloudCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: CloudSubcommands


class TerminalCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: TerminalSubcommands


class AgentsParallelCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: AgentsParallelSubcommands


class AgentsBrowserCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: AgentsBrowserSubcommands


class UtilsMachineCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: UtilsMachineSubcommands


class UtilsPyprojectCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: UtilsPyprojectSubcommands


class UtilsFileCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: UtilsFileSubcommands


class SeekCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: SeekSubcommands


DevopsConfigSubcommands = TypedDict(
    "DevopsConfigSubcommands",
    {
        "sync": LeafCommand,
        "register": LeafCommand,
        "edit": LeafCommand,
        "export-dotfiles": LeafCommand,
        "import-dotfiles": LeafCommand,
        "terminal": DevopsConfigTerminalCommand,
        "interactive": LeafCommand,
        "copy-assets": LeafCommand,
        "dump": LeafCommand,
    },
)

DevopsSelfSubcommands = TypedDict(
    "DevopsSelfSubcommands",
    {
        "install": LeafCommand,
        "update": LeafCommand,
        "status": LeafCommand,
        "security": DevopsSelfSecurityCommand,
        "explore": DevopsSelfExploreCommand,
        "readme": LeafCommand,
        "docs": LeafCommand,
        "build-installer": LeafCommand,
        "build-docker": LeafCommand,
        "build-assets": DevopsSelfBuildAssetsCommand,
        "workflows": DevopsSelfWorkflowsCommand,
    },
)

DevopsNetworkSubcommands = TypedDict(
    "DevopsNetworkSubcommands",
    {
        "share-terminal": LeafCommand,
        "share-server": LeafCommand,
        "send": LeafCommand,
        "receive": LeafCommand,
        "share-temp-file": LeafCommand,
        "ssh": DevopsNetworkSshCommand,
        "device": DevopsNetworkDeviceCommand,
        "show-address": LeafCommand,
        "vscode-share": LeafCommand,
    },
)

AgentsSubcommands = TypedDict(
    "AgentsSubcommands",
    {
        "parallel": AgentsParallelCommand,
        "browser": AgentsBrowserCommand,
        "add-mcp": LeafCommand,
        "add-skill": LeafCommand,
        "add-todo": LeafCommand,
        "add-symlinks": LeafCommand,
        "add-config": LeafCommand,
        "run-prompt": LeafCommand,
        "ask": LeafCommand,
    },
)

UtilsSubcommands = TypedDict(
    "UtilsSubcommands",
    {
        "machine": UtilsMachineCommand,
        "pyproject": UtilsPyprojectCommand,
        "file": UtilsFileCommand,
    },
)


class DevopsConfigCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsConfigSubcommands


class DevopsSelfCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsSelfSubcommands


class DevopsNetworkCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsNetworkSubcommands


class AgentsCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: AgentsSubcommands


class UtilsCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: UtilsSubcommands


DevopsSubcommands = TypedDict(
    "DevopsSubcommands",
    {
        "install": LeafCommand,
        "repos": DevopsReposCommand,
        "config": DevopsConfigCommand,
        "data": DevopsDataCommand,
        "self": DevopsSelfCommand,
        "network": DevopsNetworkCommand,
        "execute": LeafCommand,
    },
)


class DevopsCommand(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: DevopsSubcommands


StackOpsSubcommands = TypedDict(
    "StackOpsSubcommands",
    {
        "devops": DevopsCommand,
        "cloud": CloudCommand,
        "terminal": TerminalCommand,
        "agents": AgentsCommand,
        "utils": UtilsCommand,
        "seek": SeekCommand,
        "fire": LeafCommand,
        "croshell": LeafCommand,
    },
)


class StackOpsCommandHierarchy(TypedDict):
    command_name: str
    short_name: str | None
    help: str
    subcommands: StackOpsSubcommands


DEVOPS_REPOS_SUBCOMMANDS: DevopsReposSubcommands = {
    "sync": {"command_name": "sync", "short_name": "s", "help": "📥 <s> Clone repositories described by a repos.json specification", "subcommands": {}},
    "register": {"command_name": "register", "short_name": "r", "help": "📝 <r> Record repositories into a repos.json specification", "subcommands": {}},
    "checkout-to-commit": {"command_name": "checkout-to-commit", "short_name": "ctc", "help": "🔀 [ctc] Deprecated: use sync --checkout-to-commit", "subcommands": {}},
    "checkout-to-branch": {"command_name": "checkout-to-branch", "short_name": "ctb", "help": "🔀 [ctb] Deprecated: use sync --checkout-to-branch", "subcommands": {}},
    "action": {"command_name": "action", "short_name": "a", "help": "🔄 <a> Run pull/commit/push actions across repositories", "subcommands": {}},
    "analyze": {"command_name": "analyze", "short_name": "z", "help": "📊 <z> Analyze repository development over time", "subcommands": {}},
    "guard": {"command_name": "guard", "short_name": "g", "help": "🔐 <g> Securely sync git repository to/from cloud with encryption", "subcommands": {}},
    "viz": {"command_name": "viz", "short_name": "v", "help": "🎬 <v> Visualize repository activity using Gource", "subcommands": {}},
    "count-lines": {"command_name": "count-lines", "short_name": "lc", "help": "📄 <l> Count python lines of code in current repo + historical edits.", "subcommands": {}},
    "config-linters": {"command_name": "config-linters", "short_name": "l", "help": "🧰 <l> Add linter config files to a git repository", "subcommands": {}},
    "cleanup": {"command_name": "cleanup", "short_name": "n", "help": "🧹 <n> Clean repository directories from cache files", "subcommands": {}},
}

DEVOPS_CONFIG_TERMINAL_SUBCOMMANDS: DevopsConfigTerminalSubcommands = {
    "config-shell": {"command_name": "config-shell", "short_name": "s", "help": "🐚 <s> Create or configure a shell profile.", "subcommands": {}},
    "starship-theme": {"command_name": "starship-theme", "short_name": "t", "help": "⭐ <t> Select starship prompt theme.", "subcommands": {}},
    "pwsh-theme": {"command_name": "pwsh-theme", "short_name": "T", "help": "⚡ <T> Select powershell prompt theme.", "subcommands": {}},
    "wezterm-theme": {"command_name": "wezterm-theme", "short_name": "W", "help": "💻 <W> Select WezTerm terminal theme.", "subcommands": {}},
    "ghostty-theme": {"command_name": "ghostty-theme", "short_name": "g", "help": "👻 <g> Select Ghostty terminal theme.", "subcommands": {}},
    "windows-terminal-theme": {"command_name": "windows-terminal-theme", "short_name": "x", "help": "🪟 <x> Select Windows Terminal color scheme.", "subcommands": {}},
}

DEVOPS_CONFIG_SUBCOMMANDS: DevopsConfigSubcommands = {
    "sync": {"command_name": "sync", "short_name": "s", "help": "🔄 <s> Sync dotfiles.", "subcommands": {}},
    "register": {"command_name": "register", "short_name": "r", "help": "📇 <r> Register dotfiles against user mapper.yaml", "subcommands": {}},
    "edit": {"command_name": "edit", "short_name": "e", "help": "📝 <e> Open dotfiles mapper.yaml in nano, hx, or code.", "subcommands": {}},
    "export-dotfiles": {"command_name": "export-dotfiles", "short_name": "E", "help": "📤 <E> Export dotfiles for migration to new machine.", "subcommands": {}},
    "import-dotfiles": {"command_name": "import-dotfiles", "short_name": "I", "help": "📥 <I> Import dotfiles from exported archive.", "subcommands": {}},
    "terminal": {"command_name": "terminal", "short_name": "t", "help": "🐚 <t> Configure your terminal profile.", "subcommands": DEVOPS_CONFIG_TERMINAL_SUBCOMMANDS},
    "interactive": {"command_name": "interactive", "short_name": "i", "help": "🤖 <i> Interactive configuration of machine.", "subcommands": {}},
    "copy-assets": {"command_name": "copy-assets", "short_name": "c", "help": "📋 <c> Copy asset files from library to machine.", "subcommands": {}},
    "dump": {"command_name": "dump", "short_name": "d", "help": "📦 <d> Dump example configuration files and init scripts.", "subcommands": {}},
}

DEVOPS_DATA_SUBCOMMANDS: DevopsDataSubcommands = {
    "sync": {"command_name": "sync", "short_name": "s", "help": "🔄 <s> Back up or retrieve files and directories using rclone.", "subcommands": {}},
    "register": {"command_name": "register", "short_name": "r", "help": "📝 <r> Register a new backup entry in user mapper_data.yaml.", "subcommands": {}},
    "edit": {"command_name": "edit", "short_name": "e", "help": "✏️ <e> Open backup configuration file in nano, hx, or code.", "subcommands": {}},
}

DEVOPS_SELF_SECURITY_SUBCOMMANDS: DevopsSelfSecuritySubcommands = {
    "scan": {"command_name": "scan", "short_name": "s", "help": "<s> Scan installed apps or a single file path with VirusTotal", "subcommands": {}},
    "list": {"command_name": "list", "short_name": "l", "help": "<l> List installed apps, optionally filtered by comma-separated app names", "subcommands": {}},
    "upload": {"command_name": "upload", "short_name": "u", "help": "<u> Upload a local file to cloud storage", "subcommands": {}},
    "download": {"command_name": "download", "short_name": "d", "help": "<d> Download a file from Google Drive", "subcommands": {}},
    "install": {"command_name": "install", "short_name": "i", "help": "<i> Install safe apps from app metadata report", "subcommands": {}},
    "report": {"command_name": "report", "short_name": "r", "help": "<r> Show the full saved scan report by default, or CSV rows/summary stats", "subcommands": {}},
}

DEVOPS_SELF_EXPLORE_SUBCOMMANDS: DevopsSelfExploreSubcommands = {
    "search": {"command_name": "search", "short_name": "s", "help": "🔎 <s> Search CLI graph entries and run the selected command help.", "subcommands": {}},
    "tree": {"command_name": "tree", "short_name": "t", "help": "🌳 <t> Render a rich tree view in the terminal.", "subcommands": {}},
    "dot": {"command_name": "dot", "short_name": "d", "help": "🧩 <d> Export the graph as Graphviz DOT.", "subcommands": {}},
    "view": {"command_name": "view", "short_name": "v", "help": "📊 <v> Render a Plotly hierarchy chart.", "subcommands": {}},
    "tui": {"command_name": "tui", "short_name": "u", "help": "📚 <u> NAVIGATE command structure with TUI", "subcommands": {}},
}

DEVOPS_SELF_BUILD_ASSETS_SUBCOMMANDS: DevopsSelfBuildAssetsSubcommands = {
    "update-cli-graph": {"command_name": "update-cli-graph", "short_name": "g", "help": "🧩 <g> Regenerate the checked-in CLI graph snapshot.", "subcommands": {}},
    "regenerate-charts": {"command_name": "regenerate-charts", "short_name": "c", "help": "☀ <c> Regenerate the checked-in sunburst HTML chart.", "subcommands": {}},
}

DEVOPS_SELF_WORKFLOWS_SUBCOMMANDS: DevopsSelfWorkflowsSubcommands = {
    "update-installer": {"command_name": "update-installer", "short_name": "u", "help": "🔄 <u> Create an agents layout for updating installer_data.json.", "subcommands": {}},
    "update-test": {"command_name": "update-test", "short_name": "t", "help": "🧪 <t> Create an agents layout for writing tests from repo Python sources.", "subcommands": {}},
    "update-docs": {"command_name": "update-docs", "short_name": "d", "help": "📚 <d> Create an agents layout for updating CLI and API docs only.", "subcommands": {}},
    "update-logic": {"command_name": "update-logic", "short_name": "l", "help": "🧠 <l> Create an agents layout for checking CLI command logic.", "subcommands": {}},
}

DEVOPS_SELF_SUBCOMMANDS: DevopsSelfSubcommands = {
    "install": {"command_name": "install", "short_name": "i", "help": "📋 <i> install stackops locally for nightly updates.", "subcommands": {}},
    "update": {"command_name": "update", "short_name": "u", "help": "🔄 <u> UPDATE stackops", "subcommands": {}},
    "status": {"command_name": "status", "short_name": "s", "help": "📊 <s> STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.", "subcommands": {}},
    "security": {"command_name": "security", "short_name": "y", "help": "🔐 <y> Security related CLI tools.", "subcommands": DEVOPS_SELF_SECURITY_SUBCOMMANDS},
    "explore": {"command_name": "explore", "short_name": "x", "help": "🧭 <x> Explore the StackOps CLI graph.", "subcommands": DEVOPS_SELF_EXPLORE_SUBCOMMANDS},
    "readme": {"command_name": "readme", "short_name": "r", "help": "📚 <r> render readme markdown in terminal.", "subcommands": {}},
    "docs": {"command_name": "docs", "short_name": "o", "help": "📚 <o> Serve local docs with preview URLs.", "subcommands": {}},
    "build-installer": {"command_name": "build-installer", "short_name": "e", "help": "📤 <e> Build an offline installer.", "subcommands": {}},
    "build-docker": {"command_name": "build-docker", "short_name": "d", "help": "🧱 <d> Build docker images (wraps jobs/shell/docker_build_and_publish.sh)", "subcommands": {}},
    "build-assets": {"command_name": "build-assets", "short_name": "a", "help": "🗂 <a> Regenerate repo-local CLI graph assets.", "subcommands": DEVOPS_SELF_BUILD_ASSETS_SUBCOMMANDS},
    "workflows": {"command_name": "workflows", "short_name": "w", "help": "🤖 <w> Developer AI workflows.", "subcommands": DEVOPS_SELF_WORKFLOWS_SUBCOMMANDS},
}

DEVOPS_NETWORK_SSH_SUBCOMMANDS: DevopsNetworkSshSubcommands = {
    "install-server": {"command_name": "install-server", "short_name": "i", "help": "📡 <i> Install SSH server", "subcommands": {}},
    "change-port": {"command_name": "change-port", "short_name": "p", "help": "🔌 <p> Change SSH port (Linux/WSL only)", "subcommands": {}},
    "add-key": {"command_name": "add-key", "short_name": "k", "help": "🔑 <k> Add SSH public key to this machine", "subcommands": {}},
    "debug": {"command_name": "debug", "short_name": "d", "help": "🐛 <d> Debug SSH connection", "subcommands": {}},
}

DEVOPS_NETWORK_DEVICE_SUBCOMMANDS: DevopsNetworkDeviceSubcommands = {
    "switch-public-ip": {"command_name": "switch-public-ip", "short_name": "s", "help": "🔁 <s> Switch public IP address (Cloudflare WARP)", "subcommands": {}},
    "wifi-select": {"command_name": "wifi-select", "short_name": "w", "help": "📶 <w> WiFi connection utility.", "subcommands": {}},
    "bind-wsl-port": {"command_name": "bind-wsl-port", "short_name": "b", "help": "🔌 <b> Bind WSL port to Windows host", "subcommands": {}},
    "open-wsl-port": {"command_name": "open-wsl-port", "short_name": "o", "help": "🔥 <o> Open Windows firewall ports for WSL.", "subcommands": {}},
    "link-wsl-windows": {"command_name": "link-wsl-windows", "short_name": "l", "help": "🔗 <l> Link WSL home and Windows home directories.", "subcommands": {}},
    "reset-cloudflare-tunnel": {"command_name": "reset-cloudflare-tunnel", "short_name": "r", "help": "☁ <r> Reset Cloudflare tunnel service", "subcommands": {}},
    "add-ip-exclusion-to-warp": {"command_name": "add-ip-exclusion-to-warp", "short_name": "p", "help": "🚫 <p> Add IP exclusion to WARP", "subcommands": {}},
}

DEVOPS_NETWORK_SUBCOMMANDS: DevopsNetworkSubcommands = {
    "share-terminal": {"command_name": "share-terminal", "short_name": "t", "help": "📡 <t> Share terminal via web browser", "subcommands": {}},
    "share-server": {"command_name": "share-server", "short_name": "s", "help": "🌐 <s> Start local/global server to share files/folders via web browser", "subcommands": {}},
    "send": {"command_name": "send", "short_name": "sx", "help": "📁 <sx> send files from here.", "subcommands": {}},
    "receive": {"command_name": "receive", "short_name": "rx", "help": "📁 <rx> receive files to here.", "subcommands": {}},
    "share-temp-file": {"command_name": "share-temp-file", "short_name": "T", "help": "🌡 <T> Share a file via temp.sh", "subcommands": {}},
    "ssh": {"command_name": "ssh", "short_name": "S", "help": "🔐 <S> SSH subcommands", "subcommands": DEVOPS_NETWORK_SSH_SUBCOMMANDS},
    "device": {"command_name": "device", "short_name": "d", "help": "🖥 <d> Device subcommands", "subcommands": DEVOPS_NETWORK_DEVICE_SUBCOMMANDS},
    "show-address": {"command_name": "show-address", "short_name": "a", "help": "📌 <a> Show this computer addresses on network", "subcommands": {}},
    "vscode-share": {"command_name": "vscode-share", "short_name": "v", "help": "💻 <v> Share workspace via VS Code Tunnels", "subcommands": {}},
}

DEVOPS_SUBCOMMANDS: DevopsSubcommands = {
    "install": {"command_name": "install", "short_name": "i", "help": "🔧 <i> Install essential packages", "subcommands": {}},
    "repos": {"command_name": "repos", "short_name": "r", "help": "📁 <r> Manage development repositories", "subcommands": DEVOPS_REPOS_SUBCOMMANDS},
    "config": {"command_name": "config", "short_name": "c", "help": "🔩 <c> Configuration management", "subcommands": DEVOPS_CONFIG_SUBCOMMANDS},
    "data": {"command_name": "data", "short_name": "d", "help": "💾 <d> Data management", "subcommands": DEVOPS_DATA_SUBCOMMANDS},
    "self": {"command_name": "self", "short_name": "s", "help": "🔧 <s> Self management", "subcommands": DEVOPS_SELF_SUBCOMMANDS},
    "network": {"command_name": "network", "short_name": "n", "help": "🌐 <n> Network management", "subcommands": DEVOPS_NETWORK_SUBCOMMANDS},
    "execute": {"command_name": "execute", "short_name": "e", "help": "🚀 <e> Execute python/shell scripts from pre-defined directories or as command", "subcommands": {}},
}

CLOUD_SUBCOMMANDS: CloudSubcommands = {
    "sync": {"command_name": "sync", "short_name": "s", "help": "🔄 <s> Synchronize files/folders between local and cloud storage.", "subcommands": {}},
    "copy": {"command_name": "copy", "short_name": "c", "help": "📤 <c> Upload or 📥 Download files/folders to/from cloud storage.", "subcommands": {}},
    "mount": {"command_name": "mount", "short_name": "m", "help": "🔗 <m> Mount cloud storage services as local drives.", "subcommands": {}},
    "ftpx": {"command_name": "ftpx", "short_name": "f", "help": "📦 <f> File transfer utility through SSH.", "subcommands": {}},
}

TERMINAL_SUBCOMMANDS: TerminalSubcommands = {
    "run": {"command_name": "run", "short_name": "r", "help": "<r> Run the selected layout(s)", "subcommands": {}},
    "run-all": {"command_name": "run-all", "short_name": "R", "help": "<R> Dynamically run every layout in a file", "subcommands": {}},
    "run-aoe": {"command_name": "run-aoe", "short_name": "e", "help": "<e> Run selected layout(s) through agent-of-empires", "subcommands": {}},
    "attach": {"command_name": "attach", "short_name": "a", "help": "<a> Attach to a session target", "subcommands": {}},
    "kill": {"command_name": "kill", "short_name": "k", "help": "<k> Kill a session target", "subcommands": {}},
    "trace": {"command_name": "trace", "short_name": "t", "help": "<t> Trace a tmux session until it settles", "subcommands": {}},
    "create-from-function": {"command_name": "create-from-function", "short_name": "c", "help": "<c> Create a layout from a function", "subcommands": {}},
    "balance-load": {"command_name": "balance-load", "short_name": "b", "help": "<b> Balance the load across sessions", "subcommands": {}},
    "create-template": {"command_name": "create-template", "short_name": "p", "help": "<p> Create a layout template file", "subcommands": {}},
    "summarize": {"command_name": "summarize", "short_name": "s", "help": "<s> Summarize a layout file", "subcommands": {}},
}

AGENTS_PARALLEL_SUBCOMMANDS: AgentsParallelSubcommands = {
    "create": {"command_name": "create", "short_name": "c", "help": "<c> Create agents layout file, ready to run.", "subcommands": {}},
    "create-context": {"command_name": "create-context", "short_name": "x", "help": "<x> Run prompt and ask agent to persist context", "subcommands": {}},
    "run-parallel": {"command_name": "run-parallel", "short_name": "r", "help": "<r> Run named parallel workflow from YAML", "subcommands": {}},
    "collect": {"command_name": "collect", "short_name": "T", "help": "<T> Collect all agent materials into a single file.", "subcommands": {}},
    "make-template": {"command_name": "make-template", "short_name": "p", "help": "<p> Create a template for fire agents", "subcommands": {}},
}

AGENTS_BROWSER_SUBCOMMANDS: AgentsBrowserSubcommands = {
    "install-tech": {"command_name": "install-tech", "short_name": "i", "help": "<i> Install browser automation tech", "subcommands": {}},
    "launch-browser": {"command_name": "launch-browser", "short_name": "l", "help": "<l> Launch Chrome or Brave for CDP automation", "subcommands": {}},
}

AGENTS_SUBCOMMANDS: AgentsSubcommands = {
    "parallel": {"command_name": "parallel", "short_name": "p", "help": "<p> Parallel agent workflow commands", "subcommands": AGENTS_PARALLEL_SUBCOMMANDS},
    "browser": {"command_name": "browser", "short_name": "b", "help": "<b> Browser automation commands", "subcommands": AGENTS_BROWSER_SUBCOMMANDS},
    "add-mcp": {"command_name": "add-mcp", "short_name": "m", "help": "<m> Resolve catalog MCP entries or supported skills", "subcommands": {}},
    "add-skill": {"command_name": "add-skill", "short_name": "s", "help": "<s> Add a skill to an agent", "subcommands": {}},
    "add-todo": {"command_name": "add-todo", "short_name": "d", "help": "<d> Generate a markdown file listing all Python files in the repo", "subcommands": {}},
    "add-symlinks": {"command_name": "add-symlinks", "short_name": "l", "help": "<l> Create symlinks to the current repo in ~/code_copies/", "subcommands": {}},
    "add-config": {"command_name": "add-config", "short_name": "g", "help": "<g> Initialize AI configurations in the current repository", "subcommands": {}},
    "run-prompt": {"command_name": "run-prompt", "short_name": "r", "help": "<r> Run one prompt via selected agent", "subcommands": {}},
    "ask": {"command_name": "ask", "short_name": "a", "help": "<a> Ask a selected agent directly", "subcommands": {}},
}

UTILS_MACHINE_SUBCOMMANDS: UtilsMachineSubcommands = {
    "kill-process": {"command_name": "kill-process", "short_name": "k", "help": "⚔ <k> Choose a process to kill", "subcommands": {}},
    "environment": {"command_name": "environment", "short_name": "v", "help": "⌘ <v> Navigate ENV/PATH variables. Default: fuzzy picker with preview; use --tui for Textual.", "subcommands": {}},
    "get-machine-specs": {"command_name": "get-machine-specs", "short_name": "s", "help": "🖥 <s> Get machine specifications.", "subcommands": {}},
    "list-devices": {"command_name": "list-devices", "short_name": "l", "help": "💽 <l> List available devices for mounting.", "subcommands": {}},
    "mount": {"command_name": "mount", "short_name": "m", "help": "🔌 <m> Mount a device to a mount point.", "subcommands": {}},
}

UTILS_PYPROJECT_SUBCOMMANDS: UtilsPyprojectSubcommands = {
    "init-project": {"command_name": "init-project", "short_name": "i", "help": "✦ <i> Initialize a project with a uv virtual environment and install dev packages.", "subcommands": {}},
    "upgrade-packages": {"command_name": "upgrade-packages", "short_name": "a", "help": "↑ <a> Upgrade project dependencies.", "subcommands": {}},
    "type-hint": {"command_name": "type-hint", "short_name": "t", "help": "✐ <t> Type hint a file or project directory.", "subcommands": {}},
    "type-check": {"command_name": "type-check", "short_name": "c", "help": "🧪 <c> Run the lint-and-type-check suite for a repository.", "subcommands": {}},
    "type-fix": {"command_name": "type-fix", "short_name": "f", "help": "🛠 <f> Create and run the type-fix workflow from ./.ai/linters issues files.", "subcommands": {}},
    "test-runtime": {"command_name": "test-runtime", "short_name": "tr", "help": "🧪 <R> Create and run the runtime-test workflow for Python files under the current directory.", "subcommands": {}},
    "test-reference": {"command_name": "test-reference", "short_name": "r", "help": "🔎 <r> Validate _PATH_REFERENCE targets in a repository.", "subcommands": {}},
}

UTILS_FILE_SUBCOMMANDS: UtilsFileSubcommands = {
    "edit": {"command_name": "edit", "short_name": "e", "help": "✏ <e> Open a file in the default editor.", "subcommands": {}},
    "download": {"command_name": "download", "short_name": "d", "help": "↓ <d> Download a file from a URL and optionally decompress it.", "subcommands": {}},
    "pdf-merge": {"command_name": "pdf-merge", "short_name": "p", "help": "◫ <p> Merge PDF files into one.", "subcommands": {}},
    "pdf-compress": {"command_name": "pdf-compress", "short_name": "c", "help": "↧ <c> Compress a PDF file.", "subcommands": {}},
    "read-db": {"command_name": "read-db", "short_name": "r", "help": "🗃 <r> TUI DB Visualizer.", "subcommands": {}},
}

UTILS_SUBCOMMANDS: UtilsSubcommands = {
    "machine": {"command_name": "machine", "short_name": "m", "help": "🖥 <m> Machine and device utilities", "subcommands": UTILS_MACHINE_SUBCOMMANDS},
    "pyproject": {"command_name": "pyproject", "short_name": "p", "help": "🐍 <p> Pyproject bootstrap and typing utilities", "subcommands": UTILS_PYPROJECT_SUBCOMMANDS},
    "file": {"command_name": "file", "short_name": "f", "help": "📁 <f> File, document, and database utilities", "subcommands": UTILS_FILE_SUBCOMMANDS},
}

SEEK_SUBCOMMANDS: SeekSubcommands = {
    "seek": {"command_name": "seek", "short_name": None, "help": "stackops search helper", "subcommands": {}},
}

STACKOPS_SUBCOMMANDS: StackOpsSubcommands = {
    "devops": {"command_name": "devops", "short_name": "d", "help": "<d> DevOps related commands", "subcommands": DEVOPS_SUBCOMMANDS},
    "cloud": {"command_name": "cloud", "short_name": "c", "help": "<c> Cloud management commands", "subcommands": CLOUD_SUBCOMMANDS},
    "terminal": {"command_name": "terminal", "short_name": "t", "help": "<t> Terminal and layout management", "subcommands": TERMINAL_SUBCOMMANDS},
    "agents": {"command_name": "agents", "short_name": "a", "help": "<a> 🤖 AI Agents management commands", "subcommands": AGENTS_SUBCOMMANDS},
    "utils": {"command_name": "utils", "short_name": "u", "help": "<u> Utility commands", "subcommands": UTILS_SUBCOMMANDS},
    "seek": {"command_name": "seek", "short_name": "s", "help": "<s> Search across files, text matches, and code symbols", "subcommands": SEEK_SUBCOMMANDS},
    "fire": {"command_name": "fire", "short_name": "f", "help": "<f> Fire and manage jobs", "subcommands": {}},
    "croshell": {"command_name": "croshell", "short_name": "r", "help": "<r> Cross-shell command execution", "subcommands": {}},
}

STACKOPS_CLI_HIERARCHY: StackOpsCommandHierarchy = {
    "command_name": "stackops",
    "short_name": None,
    "help": "StackOps CLI - Manage your machine configurations and workflows",
    "subcommands": STACKOPS_SUBCOMMANDS,
}
