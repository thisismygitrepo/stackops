from typing import Literal, TypedDict


EmptySubcommands = TypedDict("EmptySubcommands", {})

StackOpsDevopsInstallCommand = TypedDict(
    "StackOpsDevopsInstallCommand",
    {
        "command_name": Literal["install"],
        "short_name": Literal["i"],
        "help": Literal["🔧 <i> Install essential packages"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposSyncCommand = TypedDict(
    "StackOpsDevopsReposSyncCommand",
    {
        "command_name": Literal["sync"],
        "short_name": Literal["s"],
        "help": Literal["📥 <s> Clone repositories described by a repos.json specification"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposRegisterCommand = TypedDict(
    "StackOpsDevopsReposRegisterCommand",
    {
        "command_name": Literal["register"],
        "short_name": Literal["r"],
        "help": Literal["📝 <r> Record repositories into a repos.json specification"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposCheckoutToCommitCommand = TypedDict(
    "StackOpsDevopsReposCheckoutToCommitCommand",
    {
        "command_name": Literal["checkout-to-commit"],
        "short_name": Literal["ctc"],
        "help": Literal["🔀 [ctc] Deprecated: use sync --checkout-to-commit"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposCheckoutToBranchCommand = TypedDict(
    "StackOpsDevopsReposCheckoutToBranchCommand",
    {
        "command_name": Literal["checkout-to-branch"],
        "short_name": Literal["ctb"],
        "help": Literal["🔀 [ctb] Deprecated: use sync --checkout-to-branch"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposActionCommand = TypedDict(
    "StackOpsDevopsReposActionCommand",
    {
        "command_name": Literal["action"],
        "short_name": Literal["a"],
        "help": Literal["🔄 <a> Run pull/commit/push actions across repositories"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposAnalyzeCommand = TypedDict(
    "StackOpsDevopsReposAnalyzeCommand",
    {
        "command_name": Literal["analyze"],
        "short_name": Literal["z"],
        "help": Literal["📊 <z> Analyze repository development over time"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposGuardCommand = TypedDict(
    "StackOpsDevopsReposGuardCommand",
    {
        "command_name": Literal["guard"],
        "short_name": Literal["g"],
        "help": Literal["🔐 <g> Securely sync git repository to/from cloud with encryption"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposVizCommand = TypedDict(
    "StackOpsDevopsReposVizCommand",
    {
        "command_name": Literal["viz"],
        "short_name": Literal["v"],
        "help": Literal["🎬 <v> Visualize repository activity using Gource"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposCountLinesCommand = TypedDict(
    "StackOpsDevopsReposCountLinesCommand",
    {
        "command_name": Literal["count-lines"],
        "short_name": Literal["lc"],
        "help": Literal["📄 <l> Count python lines of code in current repo + historical edits."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposConfigLintersCommand = TypedDict(
    "StackOpsDevopsReposConfigLintersCommand",
    {
        "command_name": Literal["config-linters"],
        "short_name": Literal["l"],
        "help": Literal["🧰 <l> Add linter config files to a git repository"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposCleanupCommand = TypedDict(
    "StackOpsDevopsReposCleanupCommand",
    {
        "command_name": Literal["cleanup"],
        "short_name": Literal["n"],
        "help": Literal["🧹 <n> Clean repository directories from cache files"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsReposSubcommands = TypedDict(
    "StackOpsDevopsReposSubcommands",
    {
        "sync": StackOpsDevopsReposSyncCommand,
        "register": StackOpsDevopsReposRegisterCommand,
        "checkout-to-commit": StackOpsDevopsReposCheckoutToCommitCommand,
        "checkout-to-branch": StackOpsDevopsReposCheckoutToBranchCommand,
        "action": StackOpsDevopsReposActionCommand,
        "analyze": StackOpsDevopsReposAnalyzeCommand,
        "guard": StackOpsDevopsReposGuardCommand,
        "viz": StackOpsDevopsReposVizCommand,
        "count-lines": StackOpsDevopsReposCountLinesCommand,
        "config-linters": StackOpsDevopsReposConfigLintersCommand,
        "cleanup": StackOpsDevopsReposCleanupCommand,
    },
)

StackOpsDevopsReposCommand = TypedDict(
    "StackOpsDevopsReposCommand",
    {
        "command_name": Literal["repos"],
        "short_name": Literal["r"],
        "help": Literal["📁 <r> Manage development repositories"],
        "subcommands": StackOpsDevopsReposSubcommands,
    },
)

StackOpsDevopsConfigSyncCommand = TypedDict(
    "StackOpsDevopsConfigSyncCommand",
    {"command_name": Literal["sync"], "short_name": Literal["s"], "help": Literal["🔄 <s> Sync dotfiles."], "subcommands": EmptySubcommands},
)

StackOpsDevopsConfigRegisterCommand = TypedDict(
    "StackOpsDevopsConfigRegisterCommand",
    {
        "command_name": Literal["register"],
        "short_name": Literal["r"],
        "help": Literal["📇 <r> Register dotfiles against user mapper.yaml"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigEditCommand = TypedDict(
    "StackOpsDevopsConfigEditCommand",
    {
        "command_name": Literal["edit"],
        "short_name": Literal["e"],
        "help": Literal["📝 <e> Open dotfiles mapper.yaml in nano, hx, or code."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigExportDotfilesCommand = TypedDict(
    "StackOpsDevopsConfigExportDotfilesCommand",
    {
        "command_name": Literal["export-dotfiles"],
        "short_name": Literal["E"],
        "help": Literal["📤 <E> Export dotfiles for migration to new machine."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigImportDotfilesCommand = TypedDict(
    "StackOpsDevopsConfigImportDotfilesCommand",
    {
        "command_name": Literal["import-dotfiles"],
        "short_name": Literal["I"],
        "help": Literal["📥 <I> Import dotfiles from exported archive."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigTerminalConfigShellCommand = TypedDict(
    "StackOpsDevopsConfigTerminalConfigShellCommand",
    {
        "command_name": Literal["config-shell"],
        "short_name": Literal["s"],
        "help": Literal["🐚 <s> Create or configure a shell profile."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigTerminalStarshipThemeCommand = TypedDict(
    "StackOpsDevopsConfigTerminalStarshipThemeCommand",
    {
        "command_name": Literal["starship-theme"],
        "short_name": Literal["t"],
        "help": Literal["⭐ <t> Select starship prompt theme."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigTerminalPwshThemeCommand = TypedDict(
    "StackOpsDevopsConfigTerminalPwshThemeCommand",
    {
        "command_name": Literal["pwsh-theme"],
        "short_name": Literal["T"],
        "help": Literal["⚡ <T> Select powershell prompt theme."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigTerminalWeztermThemeCommand = TypedDict(
    "StackOpsDevopsConfigTerminalWeztermThemeCommand",
    {
        "command_name": Literal["wezterm-theme"],
        "short_name": Literal["W"],
        "help": Literal["💻 <W> Select WezTerm terminal theme."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigTerminalGhosttyThemeCommand = TypedDict(
    "StackOpsDevopsConfigTerminalGhosttyThemeCommand",
    {
        "command_name": Literal["ghostty-theme"],
        "short_name": Literal["g"],
        "help": Literal["👻 <g> Select Ghostty terminal theme."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigTerminalWindowsTerminalThemeCommand = TypedDict(
    "StackOpsDevopsConfigTerminalWindowsTerminalThemeCommand",
    {
        "command_name": Literal["windows-terminal-theme"],
        "short_name": Literal["x"],
        "help": Literal["🪟 <x> Select Windows Terminal color scheme."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigTerminalSubcommands = TypedDict(
    "StackOpsDevopsConfigTerminalSubcommands",
    {
        "config-shell": StackOpsDevopsConfigTerminalConfigShellCommand,
        "starship-theme": StackOpsDevopsConfigTerminalStarshipThemeCommand,
        "pwsh-theme": StackOpsDevopsConfigTerminalPwshThemeCommand,
        "wezterm-theme": StackOpsDevopsConfigTerminalWeztermThemeCommand,
        "ghostty-theme": StackOpsDevopsConfigTerminalGhosttyThemeCommand,
        "windows-terminal-theme": StackOpsDevopsConfigTerminalWindowsTerminalThemeCommand,
    },
)

StackOpsDevopsConfigTerminalCommand = TypedDict(
    "StackOpsDevopsConfigTerminalCommand",
    {
        "command_name": Literal["terminal"],
        "short_name": Literal["t"],
        "help": Literal["🐚 <t> Configure your terminal profile."],
        "subcommands": StackOpsDevopsConfigTerminalSubcommands,
    },
)

StackOpsDevopsConfigInteractiveCommand = TypedDict(
    "StackOpsDevopsConfigInteractiveCommand",
    {
        "command_name": Literal["interactive"],
        "short_name": Literal["i"],
        "help": Literal["🤖 <i> Interactive configuration of machine."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigCopyAssetsCommand = TypedDict(
    "StackOpsDevopsConfigCopyAssetsCommand",
    {
        "command_name": Literal["copy-assets"],
        "short_name": Literal["c"],
        "help": Literal["📋 <c> Copy asset files from library to machine."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigDumpCommand = TypedDict(
    "StackOpsDevopsConfigDumpCommand",
    {
        "command_name": Literal["dump"],
        "short_name": Literal["d"],
        "help": Literal["📦 <d> Dump example configuration files and init scripts."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsConfigSubcommands = TypedDict(
    "StackOpsDevopsConfigSubcommands",
    {
        "sync": StackOpsDevopsConfigSyncCommand,
        "register": StackOpsDevopsConfigRegisterCommand,
        "edit": StackOpsDevopsConfigEditCommand,
        "export-dotfiles": StackOpsDevopsConfigExportDotfilesCommand,
        "import-dotfiles": StackOpsDevopsConfigImportDotfilesCommand,
        "terminal": StackOpsDevopsConfigTerminalCommand,
        "interactive": StackOpsDevopsConfigInteractiveCommand,
        "copy-assets": StackOpsDevopsConfigCopyAssetsCommand,
        "dump": StackOpsDevopsConfigDumpCommand,
    },
)

StackOpsDevopsConfigCommand = TypedDict(
    "StackOpsDevopsConfigCommand",
    {
        "command_name": Literal["config"],
        "short_name": Literal["c"],
        "help": Literal["🔩 <c> Configuration management"],
        "subcommands": StackOpsDevopsConfigSubcommands,
    },
)

StackOpsDevopsDataSyncCommand = TypedDict(
    "StackOpsDevopsDataSyncCommand",
    {
        "command_name": Literal["sync"],
        "short_name": Literal["s"],
        "help": Literal["🔄 <s> Back up or retrieve files and directories using rclone."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsDataRegisterCommand = TypedDict(
    "StackOpsDevopsDataRegisterCommand",
    {
        "command_name": Literal["register"],
        "short_name": Literal["r"],
        "help": Literal["📝 <r> Register a new backup entry in user mapper/data.yaml."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsDataEditCommand = TypedDict(
    "StackOpsDevopsDataEditCommand",
    {
        "command_name": Literal["edit"],
        "short_name": Literal["e"],
        "help": Literal["✏️ <e> Open backup configuration file in nano, hx, or code."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsDataSubcommands = TypedDict(
    "StackOpsDevopsDataSubcommands",
    {"sync": StackOpsDevopsDataSyncCommand, "register": StackOpsDevopsDataRegisterCommand, "edit": StackOpsDevopsDataEditCommand},
)

StackOpsDevopsDataCommand = TypedDict(
    "StackOpsDevopsDataCommand",
    {
        "command_name": Literal["data"],
        "short_name": Literal["d"],
        "help": Literal["💾 <d> Data management"],
        "subcommands": StackOpsDevopsDataSubcommands,
    },
)

StackOpsDevopsSelfInstallCommand = TypedDict(
    "StackOpsDevopsSelfInstallCommand",
    {
        "command_name": Literal["install"],
        "short_name": Literal["i"],
        "help": Literal["📋 <i> install stackops locally for nightly updates."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfUpdateCommand = TypedDict(
    "StackOpsDevopsSelfUpdateCommand",
    {"command_name": Literal["update"], "short_name": Literal["u"], "help": Literal["🔄 <u> UPDATE stackops"], "subcommands": EmptySubcommands},
)

StackOpsDevopsSelfStatusCommand = TypedDict(
    "StackOpsDevopsSelfStatusCommand",
    {
        "command_name": Literal["status"],
        "short_name": Literal["s"],
        "help": Literal["📊 <s> STATUS of machine, shell profile, apps, symlinks, dotfiles, etc."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfSecurityScanCommand = TypedDict(
    "StackOpsDevopsSelfSecurityScanCommand",
    {
        "command_name": Literal["scan"],
        "short_name": Literal["s"],
        "help": Literal["<s> Scan installed apps or a single file path with VirusTotal"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfSecurityListCommand = TypedDict(
    "StackOpsDevopsSelfSecurityListCommand",
    {
        "command_name": Literal["list"],
        "short_name": Literal["l"],
        "help": Literal["<l> List installed apps, optionally filtered by comma-separated app names"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfSecurityUploadCommand = TypedDict(
    "StackOpsDevopsSelfSecurityUploadCommand",
    {
        "command_name": Literal["upload"],
        "short_name": Literal["u"],
        "help": Literal["<u> Upload a local file to cloud storage"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfSecurityDownloadCommand = TypedDict(
    "StackOpsDevopsSelfSecurityDownloadCommand",
    {
        "command_name": Literal["download"],
        "short_name": Literal["d"],
        "help": Literal["<d> Download a file from Google Drive"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfSecurityInstallCommand = TypedDict(
    "StackOpsDevopsSelfSecurityInstallCommand",
    {
        "command_name": Literal["install"],
        "short_name": Literal["i"],
        "help": Literal["<i> Install safe apps from app metadata report"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfSecurityReportCommand = TypedDict(
    "StackOpsDevopsSelfSecurityReportCommand",
    {
        "command_name": Literal["report"],
        "short_name": Literal["r"],
        "help": Literal["<r> Show the full saved scan report by default, or CSV rows/summary stats"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfSecuritySubcommands = TypedDict(
    "StackOpsDevopsSelfSecuritySubcommands",
    {
        "scan": StackOpsDevopsSelfSecurityScanCommand,
        "list": StackOpsDevopsSelfSecurityListCommand,
        "upload": StackOpsDevopsSelfSecurityUploadCommand,
        "download": StackOpsDevopsSelfSecurityDownloadCommand,
        "install": StackOpsDevopsSelfSecurityInstallCommand,
        "report": StackOpsDevopsSelfSecurityReportCommand,
    },
)

StackOpsDevopsSelfSecurityCommand = TypedDict(
    "StackOpsDevopsSelfSecurityCommand",
    {
        "command_name": Literal["security"],
        "short_name": Literal["y"],
        "help": Literal["🔐 <y> Security related CLI tools."],
        "subcommands": StackOpsDevopsSelfSecuritySubcommands,
    },
)

StackOpsDevopsSelfExploreSearchCommand = TypedDict(
    "StackOpsDevopsSelfExploreSearchCommand",
    {
        "command_name": Literal["search"],
        "short_name": Literal["s"],
        "help": Literal["🔎 <s> Search CLI graph entries and show the selected command summary."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfExploreTreeCommand = TypedDict(
    "StackOpsDevopsSelfExploreTreeCommand",
    {
        "command_name": Literal["tree"],
        "short_name": Literal["t"],
        "help": Literal["🌳 <t> Render a rich tree view in the terminal."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfExploreDotCommand = TypedDict(
    "StackOpsDevopsSelfExploreDotCommand",
    {
        "command_name": Literal["dot"],
        "short_name": Literal["d"],
        "help": Literal["🧩 <d> Export the graph as Graphviz DOT."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfExploreViewCommand = TypedDict(
    "StackOpsDevopsSelfExploreViewCommand",
    {
        "command_name": Literal["view"],
        "short_name": Literal["v"],
        "help": Literal["📊 <v> Render a Plotly hierarchy chart."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfExploreTuiCommand = TypedDict(
    "StackOpsDevopsSelfExploreTuiCommand",
    {
        "command_name": Literal["tui"],
        "short_name": Literal["u"],
        "help": Literal["📚 <u> NAVIGATE command structure with TUI"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfExploreSubcommands = TypedDict(
    "StackOpsDevopsSelfExploreSubcommands",
    {
        "search": StackOpsDevopsSelfExploreSearchCommand,
        "tree": StackOpsDevopsSelfExploreTreeCommand,
        "dot": StackOpsDevopsSelfExploreDotCommand,
        "view": StackOpsDevopsSelfExploreViewCommand,
        "tui": StackOpsDevopsSelfExploreTuiCommand,
    },
)

StackOpsDevopsSelfExploreCommand = TypedDict(
    "StackOpsDevopsSelfExploreCommand",
    {
        "command_name": Literal["explore"],
        "short_name": Literal["x"],
        "help": Literal["🧭 <x> Explore the StackOps CLI graph."],
        "subcommands": StackOpsDevopsSelfExploreSubcommands,
    },
)

StackOpsDevopsSelfReadmeCommand = TypedDict(
    "StackOpsDevopsSelfReadmeCommand",
    {
        "command_name": Literal["readme"],
        "short_name": Literal["r"],
        "help": Literal["📚 <r> render readme markdown in terminal."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfDocsCommand = TypedDict(
    "StackOpsDevopsSelfDocsCommand",
    {
        "command_name": Literal["docs"],
        "short_name": Literal["o"],
        "help": Literal["📚 <o> Serve local docs with preview URLs."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfBuildInstallerCommand = TypedDict(
    "StackOpsDevopsSelfBuildInstallerCommand",
    {
        "command_name": Literal["build-installer"],
        "short_name": Literal["e"],
        "help": Literal["📤 <e> Build an offline installer."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfBuildDockerCommand = TypedDict(
    "StackOpsDevopsSelfBuildDockerCommand",
    {
        "command_name": Literal["build-docker"],
        "short_name": Literal["d"],
        "help": Literal["🧱 <d> Build docker images (wraps jobs/shell/docker_build_and_publish.sh)"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfBuildAssetsUpdateCLIGraphCommand = TypedDict(
    "StackOpsDevopsSelfBuildAssetsUpdateCLIGraphCommand",
    {
        "command_name": Literal["update-cli-graph"],
        "short_name": Literal["g"],
        "help": Literal["🧩 <g> Regenerate the checked-in CLI graph snapshot."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfBuildAssetsRegenerateChartsCommand = TypedDict(
    "StackOpsDevopsSelfBuildAssetsRegenerateChartsCommand",
    {
        "command_name": Literal["regenerate-charts"],
        "short_name": Literal["c"],
        "help": Literal["☀ <c> Regenerate the checked-in sunburst HTML chart."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfBuildAssetsSubcommands = TypedDict(
    "StackOpsDevopsSelfBuildAssetsSubcommands",
    {
        "update-cli-graph": StackOpsDevopsSelfBuildAssetsUpdateCLIGraphCommand,
        "regenerate-charts": StackOpsDevopsSelfBuildAssetsRegenerateChartsCommand,
    },
)

StackOpsDevopsSelfBuildAssetsCommand = TypedDict(
    "StackOpsDevopsSelfBuildAssetsCommand",
    {
        "command_name": Literal["build-assets"],
        "short_name": Literal["a"],
        "help": Literal["🗂 <a> Regenerate repo-local CLI graph assets."],
        "subcommands": StackOpsDevopsSelfBuildAssetsSubcommands,
    },
)

StackOpsDevopsSelfWorkflowsUpdateInstallerCommand = TypedDict(
    "StackOpsDevopsSelfWorkflowsUpdateInstallerCommand",
    {
        "command_name": Literal["update-installer"],
        "short_name": Literal["u"],
        "help": Literal["🔄 <u> Create an agents layout for updating installer_data.json."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfWorkflowsUpdateTestCommand = TypedDict(
    "StackOpsDevopsSelfWorkflowsUpdateTestCommand",
    {
        "command_name": Literal["update-test"],
        "short_name": Literal["t"],
        "help": Literal["🧪 <t> Create an agents layout for writing tests from repo Python sources."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfWorkflowsUpdateDocsCommand = TypedDict(
    "StackOpsDevopsSelfWorkflowsUpdateDocsCommand",
    {
        "command_name": Literal["update-docs"],
        "short_name": Literal["d"],
        "help": Literal["📚 <d> Create an agents layout for updating CLI and API docs only."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfWorkflowsUpdateLogicCommand = TypedDict(
    "StackOpsDevopsSelfWorkflowsUpdateLogicCommand",
    {
        "command_name": Literal["update-logic"],
        "short_name": Literal["l"],
        "help": Literal["🧠 <l> Create an agents layout for checking CLI command logic."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSelfWorkflowsSubcommands = TypedDict(
    "StackOpsDevopsSelfWorkflowsSubcommands",
    {
        "update-installer": StackOpsDevopsSelfWorkflowsUpdateInstallerCommand,
        "update-test": StackOpsDevopsSelfWorkflowsUpdateTestCommand,
        "update-docs": StackOpsDevopsSelfWorkflowsUpdateDocsCommand,
        "update-logic": StackOpsDevopsSelfWorkflowsUpdateLogicCommand,
    },
)

StackOpsDevopsSelfWorkflowsCommand = TypedDict(
    "StackOpsDevopsSelfWorkflowsCommand",
    {
        "command_name": Literal["workflows"],
        "short_name": Literal["w"],
        "help": Literal["🤖 <w> Developer AI workflows."],
        "subcommands": StackOpsDevopsSelfWorkflowsSubcommands,
    },
)

StackOpsDevopsSelfSubcommands = TypedDict(
    "StackOpsDevopsSelfSubcommands",
    {
        "install": StackOpsDevopsSelfInstallCommand,
        "update": StackOpsDevopsSelfUpdateCommand,
        "status": StackOpsDevopsSelfStatusCommand,
        "security": StackOpsDevopsSelfSecurityCommand,
        "explore": StackOpsDevopsSelfExploreCommand,
        "readme": StackOpsDevopsSelfReadmeCommand,
        "docs": StackOpsDevopsSelfDocsCommand,
        "build-installer": StackOpsDevopsSelfBuildInstallerCommand,
        "build-docker": StackOpsDevopsSelfBuildDockerCommand,
        "build-assets": StackOpsDevopsSelfBuildAssetsCommand,
        "workflows": StackOpsDevopsSelfWorkflowsCommand,
    },
)

StackOpsDevopsSelfCommand = TypedDict(
    "StackOpsDevopsSelfCommand",
    {
        "command_name": Literal["self"],
        "short_name": Literal["s"],
        "help": Literal["🔧 <s> Self management"],
        "subcommands": StackOpsDevopsSelfSubcommands,
    },
)

StackOpsDevopsNetworkShareTerminalCommand = TypedDict(
    "StackOpsDevopsNetworkShareTerminalCommand",
    {
        "command_name": Literal["share-terminal"],
        "short_name": Literal["t"],
        "help": Literal["📡 <t> Share terminal via web browser"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkShareServerCommand = TypedDict(
    "StackOpsDevopsNetworkShareServerCommand",
    {
        "command_name": Literal["share-server"],
        "short_name": Literal["s"],
        "help": Literal["🌐 <s> Start local/global server to share files/folders via web browser"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkSendCommand = TypedDict(
    "StackOpsDevopsNetworkSendCommand",
    {"command_name": Literal["send"], "short_name": Literal["sx"], "help": Literal["📁 <sx> send files from here."], "subcommands": EmptySubcommands},
)

StackOpsDevopsNetworkReceiveCommand = TypedDict(
    "StackOpsDevopsNetworkReceiveCommand",
    {
        "command_name": Literal["receive"],
        "short_name": Literal["rx"],
        "help": Literal["📁 <rx> receive files to here."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkShareTempFileCommand = TypedDict(
    "StackOpsDevopsNetworkShareTempFileCommand",
    {
        "command_name": Literal["share-temp-file"],
        "short_name": Literal["T"],
        "help": Literal["🌡 <T> Share a file via temp.sh"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkSSHInstallServerCommand = TypedDict(
    "StackOpsDevopsNetworkSSHInstallServerCommand",
    {
        "command_name": Literal["install-server"],
        "short_name": Literal["i"],
        "help": Literal["📡 <i> Install SSH server"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkSSHChangePortCommand = TypedDict(
    "StackOpsDevopsNetworkSSHChangePortCommand",
    {
        "command_name": Literal["change-port"],
        "short_name": Literal["p"],
        "help": Literal["🔌 <p> Change SSH port (Linux/WSL only)"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkSSHAddKeyCommand = TypedDict(
    "StackOpsDevopsNetworkSSHAddKeyCommand",
    {
        "command_name": Literal["add-key"],
        "short_name": Literal["k"],
        "help": Literal["🔑 <k> Add SSH public key to this machine"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkSSHDebugCommand = TypedDict(
    "StackOpsDevopsNetworkSSHDebugCommand",
    {"command_name": Literal["debug"], "short_name": Literal["d"], "help": Literal["🐛 <d> Debug SSH connection"], "subcommands": EmptySubcommands},
)

StackOpsDevopsNetworkSSHSubcommands = TypedDict(
    "StackOpsDevopsNetworkSSHSubcommands",
    {
        "install-server": StackOpsDevopsNetworkSSHInstallServerCommand,
        "change-port": StackOpsDevopsNetworkSSHChangePortCommand,
        "add-key": StackOpsDevopsNetworkSSHAddKeyCommand,
        "debug": StackOpsDevopsNetworkSSHDebugCommand,
    },
)

StackOpsDevopsNetworkSSHCommand = TypedDict(
    "StackOpsDevopsNetworkSSHCommand",
    {
        "command_name": Literal["ssh"],
        "short_name": Literal["S"],
        "help": Literal["🔐 <S> SSH subcommands"],
        "subcommands": StackOpsDevopsNetworkSSHSubcommands,
    },
)

StackOpsDevopsNetworkDeviceSwitchPublicIpCommand = TypedDict(
    "StackOpsDevopsNetworkDeviceSwitchPublicIpCommand",
    {
        "command_name": Literal["switch-public-ip"],
        "short_name": Literal["s"],
        "help": Literal["🔁 <s> Switch public IP address (Cloudflare WARP)"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkDeviceWifiSelectCommand = TypedDict(
    "StackOpsDevopsNetworkDeviceWifiSelectCommand",
    {
        "command_name": Literal["wifi-select"],
        "short_name": Literal["w"],
        "help": Literal["📶 <w> WiFi connection utility."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkDeviceBindWSLPortCommand = TypedDict(
    "StackOpsDevopsNetworkDeviceBindWSLPortCommand",
    {
        "command_name": Literal["bind-wsl-port"],
        "short_name": Literal["b"],
        "help": Literal["🔌 <b> Bind WSL port to Windows host"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkDeviceOpenWSLPortCommand = TypedDict(
    "StackOpsDevopsNetworkDeviceOpenWSLPortCommand",
    {
        "command_name": Literal["open-wsl-port"],
        "short_name": Literal["o"],
        "help": Literal["🔥 <o> Open Windows firewall ports for WSL."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkDeviceLinkWSLWindowsCommand = TypedDict(
    "StackOpsDevopsNetworkDeviceLinkWSLWindowsCommand",
    {
        "command_name": Literal["link-wsl-windows"],
        "short_name": Literal["l"],
        "help": Literal["🔗 <l> Link WSL home and Windows home directories."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkDeviceResetCloudflareTunnelCommand = TypedDict(
    "StackOpsDevopsNetworkDeviceResetCloudflareTunnelCommand",
    {
        "command_name": Literal["reset-cloudflare-tunnel"],
        "short_name": Literal["r"],
        "help": Literal["☁ <r> Reset Cloudflare tunnel service"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkDeviceAddIpExclusionToWarpCommand = TypedDict(
    "StackOpsDevopsNetworkDeviceAddIpExclusionToWarpCommand",
    {
        "command_name": Literal["add-ip-exclusion-to-warp"],
        "short_name": Literal["p"],
        "help": Literal["🚫 <p> Add IP exclusion to WARP"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkDeviceSubcommands = TypedDict(
    "StackOpsDevopsNetworkDeviceSubcommands",
    {
        "switch-public-ip": StackOpsDevopsNetworkDeviceSwitchPublicIpCommand,
        "wifi-select": StackOpsDevopsNetworkDeviceWifiSelectCommand,
        "bind-wsl-port": StackOpsDevopsNetworkDeviceBindWSLPortCommand,
        "open-wsl-port": StackOpsDevopsNetworkDeviceOpenWSLPortCommand,
        "link-wsl-windows": StackOpsDevopsNetworkDeviceLinkWSLWindowsCommand,
        "reset-cloudflare-tunnel": StackOpsDevopsNetworkDeviceResetCloudflareTunnelCommand,
        "add-ip-exclusion-to-warp": StackOpsDevopsNetworkDeviceAddIpExclusionToWarpCommand,
    },
)

StackOpsDevopsNetworkDeviceCommand = TypedDict(
    "StackOpsDevopsNetworkDeviceCommand",
    {
        "command_name": Literal["device"],
        "short_name": Literal["d"],
        "help": Literal["🖥 <d> Device subcommands"],
        "subcommands": StackOpsDevopsNetworkDeviceSubcommands,
    },
)

StackOpsDevopsNetworkShowAddressCommand = TypedDict(
    "StackOpsDevopsNetworkShowAddressCommand",
    {
        "command_name": Literal["show-address"],
        "short_name": Literal["a"],
        "help": Literal["📌 <a> Show this computer addresses on network"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkVscodeShareCommand = TypedDict(
    "StackOpsDevopsNetworkVscodeShareCommand",
    {
        "command_name": Literal["vscode-share"],
        "short_name": Literal["v"],
        "help": Literal["💻 <v> Share workspace via VS Code Tunnels"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsNetworkSubcommands = TypedDict(
    "StackOpsDevopsNetworkSubcommands",
    {
        "share-terminal": StackOpsDevopsNetworkShareTerminalCommand,
        "share-server": StackOpsDevopsNetworkShareServerCommand,
        "send": StackOpsDevopsNetworkSendCommand,
        "receive": StackOpsDevopsNetworkReceiveCommand,
        "share-temp-file": StackOpsDevopsNetworkShareTempFileCommand,
        "ssh": StackOpsDevopsNetworkSSHCommand,
        "device": StackOpsDevopsNetworkDeviceCommand,
        "show-address": StackOpsDevopsNetworkShowAddressCommand,
        "vscode-share": StackOpsDevopsNetworkVscodeShareCommand,
    },
)

StackOpsDevopsNetworkCommand = TypedDict(
    "StackOpsDevopsNetworkCommand",
    {
        "command_name": Literal["network"],
        "short_name": Literal["n"],
        "help": Literal["🌐 <n> Network management"],
        "subcommands": StackOpsDevopsNetworkSubcommands,
    },
)

StackOpsDevopsExecuteCommand = TypedDict(
    "StackOpsDevopsExecuteCommand",
    {
        "command_name": Literal["execute"],
        "short_name": Literal["e"],
        "help": Literal["🚀 <e> Execute python/shell scripts from pre-defined directories or as command"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsDevopsSubcommands = TypedDict(
    "StackOpsDevopsSubcommands",
    {
        "install": StackOpsDevopsInstallCommand,
        "repos": StackOpsDevopsReposCommand,
        "config": StackOpsDevopsConfigCommand,
        "data": StackOpsDevopsDataCommand,
        "self": StackOpsDevopsSelfCommand,
        "network": StackOpsDevopsNetworkCommand,
        "execute": StackOpsDevopsExecuteCommand,
    },
)

StackOpsDevopsCommand = TypedDict(
    "StackOpsDevopsCommand",
    {
        "command_name": Literal["devops"],
        "short_name": Literal["d"],
        "help": Literal["<d> DevOps related commands"],
        "subcommands": StackOpsDevopsSubcommands,
    },
)

StackOpsCloudSyncCommand = TypedDict(
    "StackOpsCloudSyncCommand",
    {
        "command_name": Literal["sync"],
        "short_name": Literal["s"],
        "help": Literal["🔄 <s> Synchronize files/folders between local and cloud storage."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsCloudCopyCommand = TypedDict(
    "StackOpsCloudCopyCommand",
    {
        "command_name": Literal["copy"],
        "short_name": Literal["c"],
        "help": Literal["📤 <c> Upload or 📥 Download files/folders to/from cloud storage."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsCloudMountCommand = TypedDict(
    "StackOpsCloudMountCommand",
    {
        "command_name": Literal["mount"],
        "short_name": Literal["m"],
        "help": Literal["🔗 <m> Mount cloud storage services as local drives."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsCloudFtpxCommand = TypedDict(
    "StackOpsCloudFtpxCommand",
    {
        "command_name": Literal["ftpx"],
        "short_name": Literal["f"],
        "help": Literal["📦 <f> File transfer utility through SSH."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsCloudSubcommands = TypedDict(
    "StackOpsCloudSubcommands",
    {"sync": StackOpsCloudSyncCommand, "copy": StackOpsCloudCopyCommand, "mount": StackOpsCloudMountCommand, "ftpx": StackOpsCloudFtpxCommand},
)

StackOpsCloudCommand = TypedDict(
    "StackOpsCloudCommand",
    {
        "command_name": Literal["cloud"],
        "short_name": Literal["c"],
        "help": Literal["<c> Cloud management commands"],
        "subcommands": StackOpsCloudSubcommands,
    },
)

StackOpsTerminalRunCommand = TypedDict(
    "StackOpsTerminalRunCommand",
    {"command_name": Literal["run"], "short_name": Literal["r"], "help": Literal["<r> Run the selected layout(s)"], "subcommands": EmptySubcommands},
)

StackOpsTerminalRunAllCommand = TypedDict(
    "StackOpsTerminalRunAllCommand",
    {
        "command_name": Literal["run-all"],
        "short_name": Literal["R"],
        "help": Literal["<R> Dynamically run every layout in a file"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsTerminalRunAoeCommand = TypedDict(
    "StackOpsTerminalRunAoeCommand",
    {
        "command_name": Literal["run-aoe"],
        "short_name": Literal["e"],
        "help": Literal["<e> Run selected layout(s) through agent-of-empires"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsTerminalAttachCommand = TypedDict(
    "StackOpsTerminalAttachCommand",
    {
        "command_name": Literal["attach"],
        "short_name": Literal["a"],
        "help": Literal["<a> Attach to a session target"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsTerminalKillCommand = TypedDict(
    "StackOpsTerminalKillCommand",
    {"command_name": Literal["kill"], "short_name": Literal["k"], "help": Literal["<k> Kill a session target"], "subcommands": EmptySubcommands},
)

StackOpsTerminalTraceCommand = TypedDict(
    "StackOpsTerminalTraceCommand",
    {
        "command_name": Literal["trace"],
        "short_name": Literal["t"],
        "help": Literal["<t> Trace a tmux session until it settles"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsTerminalCreateFromFunctionCommand = TypedDict(
    "StackOpsTerminalCreateFromFunctionCommand",
    {
        "command_name": Literal["create-from-function"],
        "short_name": Literal["c"],
        "help": Literal["<c> Create a layout from a function"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsTerminalBalanceLoadCommand = TypedDict(
    "StackOpsTerminalBalanceLoadCommand",
    {
        "command_name": Literal["balance-load"],
        "short_name": Literal["b"],
        "help": Literal["<b> Balance the load across sessions"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsTerminalCreateTemplateCommand = TypedDict(
    "StackOpsTerminalCreateTemplateCommand",
    {
        "command_name": Literal["create-template"],
        "short_name": Literal["p"],
        "help": Literal["<p> Create a layout template file"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsTerminalSummarizeCommand = TypedDict(
    "StackOpsTerminalSummarizeCommand",
    {
        "command_name": Literal["summarize"],
        "short_name": Literal["s"],
        "help": Literal["<s> Summarize a layout file"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsTerminalSubcommands = TypedDict(
    "StackOpsTerminalSubcommands",
    {
        "run": StackOpsTerminalRunCommand,
        "run-all": StackOpsTerminalRunAllCommand,
        "run-aoe": StackOpsTerminalRunAoeCommand,
        "attach": StackOpsTerminalAttachCommand,
        "kill": StackOpsTerminalKillCommand,
        "trace": StackOpsTerminalTraceCommand,
        "create-from-function": StackOpsTerminalCreateFromFunctionCommand,
        "balance-load": StackOpsTerminalBalanceLoadCommand,
        "create-template": StackOpsTerminalCreateTemplateCommand,
        "summarize": StackOpsTerminalSummarizeCommand,
    },
)

StackOpsTerminalCommand = TypedDict(
    "StackOpsTerminalCommand",
    {
        "command_name": Literal["terminal"],
        "short_name": Literal["t"],
        "help": Literal["<t> Terminal and layout management"],
        "subcommands": StackOpsTerminalSubcommands,
    },
)

StackOpsAgentsParallelCreateCommand = TypedDict(
    "StackOpsAgentsParallelCreateCommand",
    {
        "command_name": Literal["create"],
        "short_name": Literal["c"],
        "help": Literal["<c> Create agents layout file, ready to run."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsParallelCreateContextCommand = TypedDict(
    "StackOpsAgentsParallelCreateContextCommand",
    {
        "command_name": Literal["create-context"],
        "short_name": Literal["x"],
        "help": Literal["<x> Run prompt and ask agent to persist context"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsParallelRunParallelCommand = TypedDict(
    "StackOpsAgentsParallelRunParallelCommand",
    {
        "command_name": Literal["run-parallel"],
        "short_name": Literal["r"],
        "help": Literal["<r> Run named parallel workflow from YAML"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsParallelCollectCommand = TypedDict(
    "StackOpsAgentsParallelCollectCommand",
    {
        "command_name": Literal["collect"],
        "short_name": Literal["T"],
        "help": Literal["<T> Collect all agent materials into a single file."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsParallelMakeTemplateCommand = TypedDict(
    "StackOpsAgentsParallelMakeTemplateCommand",
    {
        "command_name": Literal["make-template"],
        "short_name": Literal["p"],
        "help": Literal["<p> Create a template for fire agents"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsParallelSubcommands = TypedDict(
    "StackOpsAgentsParallelSubcommands",
    {
        "create": StackOpsAgentsParallelCreateCommand,
        "create-context": StackOpsAgentsParallelCreateContextCommand,
        "run-parallel": StackOpsAgentsParallelRunParallelCommand,
        "collect": StackOpsAgentsParallelCollectCommand,
        "make-template": StackOpsAgentsParallelMakeTemplateCommand,
    },
)

StackOpsAgentsParallelCommand = TypedDict(
    "StackOpsAgentsParallelCommand",
    {
        "command_name": Literal["parallel"],
        "short_name": Literal["p"],
        "help": Literal["<p> Parallel agent workflow commands"],
        "subcommands": StackOpsAgentsParallelSubcommands,
    },
)

StackOpsAgentsBrowserInstallTechCommand = TypedDict(
    "StackOpsAgentsBrowserInstallTechCommand",
    {
        "command_name": Literal["install-tech"],
        "short_name": Literal["i"],
        "help": Literal["<i> Install browser automation tech"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsBrowserLaunchBrowserCommand = TypedDict(
    "StackOpsAgentsBrowserLaunchBrowserCommand",
    {
        "command_name": Literal["launch-browser"],
        "short_name": Literal["l"],
        "help": Literal["<l> Launch Chrome or Brave for CDP automation"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsBrowserSubcommands = TypedDict(
    "StackOpsAgentsBrowserSubcommands",
    {"install-tech": StackOpsAgentsBrowserInstallTechCommand, "launch-browser": StackOpsAgentsBrowserLaunchBrowserCommand},
)

StackOpsAgentsBrowserCommand = TypedDict(
    "StackOpsAgentsBrowserCommand",
    {
        "command_name": Literal["browser"],
        "short_name": Literal["b"],
        "help": Literal["<b> Browser automation commands"],
        "subcommands": StackOpsAgentsBrowserSubcommands,
    },
)

StackOpsAgentsAddMcpCommand = TypedDict(
    "StackOpsAgentsAddMcpCommand",
    {
        "command_name": Literal["add-mcp"],
        "short_name": Literal["m"],
        "help": Literal["<m> Resolve catalog MCP entries or supported skills"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsAddSkillCommand = TypedDict(
    "StackOpsAgentsAddSkillCommand",
    {
        "command_name": Literal["add-skill"],
        "short_name": Literal["s"],
        "help": Literal["<s> Add a skill to an agent"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsAddTodoCommand = TypedDict(
    "StackOpsAgentsAddTodoCommand",
    {
        "command_name": Literal["add-todo"],
        "short_name": Literal["d"],
        "help": Literal["<d> Generate a markdown file listing all Python files in the repo"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsAddSymlinksCommand = TypedDict(
    "StackOpsAgentsAddSymlinksCommand",
    {
        "command_name": Literal["add-symlinks"],
        "short_name": Literal["l"],
        "help": Literal["<l> Create symlinks to the current repo in ~/code_copies/"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsAddConfigCommand = TypedDict(
    "StackOpsAgentsAddConfigCommand",
    {
        "command_name": Literal["add-config"],
        "short_name": Literal["g"],
        "help": Literal["<g> Initialize AI configurations in the current repository"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsRunPromptCommand = TypedDict(
    "StackOpsAgentsRunPromptCommand",
    {
        "command_name": Literal["run-prompt"],
        "short_name": Literal["r"],
        "help": Literal["<r> Run one prompt via selected agent"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsAskCommand = TypedDict(
    "StackOpsAgentsAskCommand",
    {
        "command_name": Literal["ask"],
        "short_name": Literal["a"],
        "help": Literal["<a> Ask a selected agent directly"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsAgentsSubcommands = TypedDict(
    "StackOpsAgentsSubcommands",
    {
        "parallel": StackOpsAgentsParallelCommand,
        "browser": StackOpsAgentsBrowserCommand,
        "add-mcp": StackOpsAgentsAddMcpCommand,
        "add-skill": StackOpsAgentsAddSkillCommand,
        "add-todo": StackOpsAgentsAddTodoCommand,
        "add-symlinks": StackOpsAgentsAddSymlinksCommand,
        "add-config": StackOpsAgentsAddConfigCommand,
        "run-prompt": StackOpsAgentsRunPromptCommand,
        "ask": StackOpsAgentsAskCommand,
    },
)

StackOpsAgentsCommand = TypedDict(
    "StackOpsAgentsCommand",
    {
        "command_name": Literal["agents"],
        "short_name": Literal["a"],
        "help": Literal["<a> 🤖 AI Agents management commands"],
        "subcommands": StackOpsAgentsSubcommands,
    },
)

StackOpsUtilsMachineKillProcessCommand = TypedDict(
    "StackOpsUtilsMachineKillProcessCommand",
    {
        "command_name": Literal["kill-process"],
        "short_name": Literal["k"],
        "help": Literal["⚔ <k> Choose a process to kill"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsMachineEnvironmentCommand = TypedDict(
    "StackOpsUtilsMachineEnvironmentCommand",
    {
        "command_name": Literal["environment"],
        "short_name": Literal["v"],
        "help": Literal["⌘ <v> Navigate ENV/PATH variables. Default: fuzzy picker with preview; use --tui for Textual."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsMachineGetMachineSpecsCommand = TypedDict(
    "StackOpsUtilsMachineGetMachineSpecsCommand",
    {
        "command_name": Literal["get-machine-specs"],
        "short_name": Literal["s"],
        "help": Literal["🖥 <s> Get machine specifications."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsMachineListDevicesCommand = TypedDict(
    "StackOpsUtilsMachineListDevicesCommand",
    {
        "command_name": Literal["list-devices"],
        "short_name": Literal["l"],
        "help": Literal["💽 <l> List available devices for mounting."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsMachineMountCommand = TypedDict(
    "StackOpsUtilsMachineMountCommand",
    {
        "command_name": Literal["mount"],
        "short_name": Literal["m"],
        "help": Literal["🔌 <m> Mount a device to a mount point."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsMachineSubcommands = TypedDict(
    "StackOpsUtilsMachineSubcommands",
    {
        "kill-process": StackOpsUtilsMachineKillProcessCommand,
        "environment": StackOpsUtilsMachineEnvironmentCommand,
        "get-machine-specs": StackOpsUtilsMachineGetMachineSpecsCommand,
        "list-devices": StackOpsUtilsMachineListDevicesCommand,
        "mount": StackOpsUtilsMachineMountCommand,
    },
)

StackOpsUtilsMachineCommand = TypedDict(
    "StackOpsUtilsMachineCommand",
    {
        "command_name": Literal["machine"],
        "short_name": Literal["m"],
        "help": Literal["🖥 <m> Machine and device utilities"],
        "subcommands": StackOpsUtilsMachineSubcommands,
    },
)

StackOpsUtilsPyprojectInitProjectCommand = TypedDict(
    "StackOpsUtilsPyprojectInitProjectCommand",
    {
        "command_name": Literal["init-project"],
        "short_name": Literal["i"],
        "help": Literal["✦ <i> Initialize a project with a uv virtual environment and install dev packages."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsPyprojectUpgradePackagesCommand = TypedDict(
    "StackOpsUtilsPyprojectUpgradePackagesCommand",
    {
        "command_name": Literal["upgrade-packages"],
        "short_name": Literal["a"],
        "help": Literal["↑ <a> Upgrade project dependencies."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsPyprojectTypeHintCommand = TypedDict(
    "StackOpsUtilsPyprojectTypeHintCommand",
    {
        "command_name": Literal["type-hint"],
        "short_name": Literal["t"],
        "help": Literal["✐ <t> Type hint a file or project directory."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsPyprojectTypeCheckCommand = TypedDict(
    "StackOpsUtilsPyprojectTypeCheckCommand",
    {
        "command_name": Literal["type-check"],
        "short_name": Literal["c"],
        "help": Literal["🧪 <c> Run the lint-and-type-check suite for a repository."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsPyprojectTypeFixCommand = TypedDict(
    "StackOpsUtilsPyprojectTypeFixCommand",
    {
        "command_name": Literal["type-fix"],
        "short_name": Literal["f"],
        "help": Literal["🛠 <f> Create and run the type-fix workflow from ./.ai/linters issues files."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsPyprojectTestRuntimeCommand = TypedDict(
    "StackOpsUtilsPyprojectTestRuntimeCommand",
    {
        "command_name": Literal["test-runtime"],
        "short_name": Literal["tr"],
        "help": Literal["🧪 <R> Create and run the runtime-test workflow for Python files under the current directory."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsPyprojectTestReferenceCommand = TypedDict(
    "StackOpsUtilsPyprojectTestReferenceCommand",
    {
        "command_name": Literal["test-reference"],
        "short_name": Literal["r"],
        "help": Literal["🔎 <r> Validate _PATH_REFERENCE targets in a repository."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsPyprojectSubcommands = TypedDict(
    "StackOpsUtilsPyprojectSubcommands",
    {
        "init-project": StackOpsUtilsPyprojectInitProjectCommand,
        "upgrade-packages": StackOpsUtilsPyprojectUpgradePackagesCommand,
        "type-hint": StackOpsUtilsPyprojectTypeHintCommand,
        "type-check": StackOpsUtilsPyprojectTypeCheckCommand,
        "type-fix": StackOpsUtilsPyprojectTypeFixCommand,
        "test-runtime": StackOpsUtilsPyprojectTestRuntimeCommand,
        "test-reference": StackOpsUtilsPyprojectTestReferenceCommand,
    },
)

StackOpsUtilsPyprojectCommand = TypedDict(
    "StackOpsUtilsPyprojectCommand",
    {
        "command_name": Literal["pyproject"],
        "short_name": Literal["p"],
        "help": Literal["🐍 <p> Pyproject bootstrap and typing utilities"],
        "subcommands": StackOpsUtilsPyprojectSubcommands,
    },
)

StackOpsUtilsFileEditCommand = TypedDict(
    "StackOpsUtilsFileEditCommand",
    {
        "command_name": Literal["edit"],
        "short_name": Literal["e"],
        "help": Literal["✏ <e> Open a file in the default editor."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsFileDownloadCommand = TypedDict(
    "StackOpsUtilsFileDownloadCommand",
    {
        "command_name": Literal["download"],
        "short_name": Literal["d"],
        "help": Literal["↓ <d> Download a file from a URL and optionally decompress it."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsFilePDFMergeCommand = TypedDict(
    "StackOpsUtilsFilePDFMergeCommand",
    {
        "command_name": Literal["pdf-merge"],
        "short_name": Literal["p"],
        "help": Literal["◫ <p> Merge PDF files into one."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsFilePDFCompressCommand = TypedDict(
    "StackOpsUtilsFilePDFCompressCommand",
    {
        "command_name": Literal["pdf-compress"],
        "short_name": Literal["c"],
        "help": Literal["↧ <c> Compress a PDF file."],
        "subcommands": EmptySubcommands,
    },
)

StackOpsUtilsFileReadDBCommand = TypedDict(
    "StackOpsUtilsFileReadDBCommand",
    {"command_name": Literal["read-db"], "short_name": Literal["r"], "help": Literal["🗃 <r> TUI DB Visualizer."], "subcommands": EmptySubcommands},
)

StackOpsUtilsFileSubcommands = TypedDict(
    "StackOpsUtilsFileSubcommands",
    {
        "edit": StackOpsUtilsFileEditCommand,
        "download": StackOpsUtilsFileDownloadCommand,
        "pdf-merge": StackOpsUtilsFilePDFMergeCommand,
        "pdf-compress": StackOpsUtilsFilePDFCompressCommand,
        "read-db": StackOpsUtilsFileReadDBCommand,
    },
)

StackOpsUtilsFileCommand = TypedDict(
    "StackOpsUtilsFileCommand",
    {
        "command_name": Literal["file"],
        "short_name": Literal["f"],
        "help": Literal["📁 <f> File, document, and database utilities"],
        "subcommands": StackOpsUtilsFileSubcommands,
    },
)

StackOpsUtilsSubcommands = TypedDict(
    "StackOpsUtilsSubcommands", {"machine": StackOpsUtilsMachineCommand, "pyproject": StackOpsUtilsPyprojectCommand, "file": StackOpsUtilsFileCommand}
)

StackOpsUtilsCommand = TypedDict(
    "StackOpsUtilsCommand",
    {"command_name": Literal["utils"], "short_name": Literal["u"], "help": Literal["<u> Utility commands"], "subcommands": StackOpsUtilsSubcommands},
)

StackOpsSeekSeekCommand = TypedDict(
    "StackOpsSeekSeekCommand",
    {"command_name": Literal["seek"], "short_name": Literal[None], "help": Literal["stackops search helper"], "subcommands": EmptySubcommands},
)

StackOpsSeekSubcommands = TypedDict("StackOpsSeekSubcommands", {"seek": StackOpsSeekSeekCommand})

StackOpsSeekCommand = TypedDict(
    "StackOpsSeekCommand",
    {
        "command_name": Literal["seek"],
        "short_name": Literal["s"],
        "help": Literal["<s> Search across files, text matches, and code symbols"],
        "subcommands": StackOpsSeekSubcommands,
    },
)

StackOpsFireCommand = TypedDict(
    "StackOpsFireCommand",
    {"command_name": Literal["fire"], "short_name": Literal["f"], "help": Literal["<f> Fire and manage jobs"], "subcommands": EmptySubcommands},
)

StackOpsPreviewCommand = TypedDict(
    "StackOpsPreviewCommand",
    {
        "command_name": Literal["preview"],
        "short_name": Literal["p"],
        "help": Literal["<p> Preview files and launch reader backends"],
        "subcommands": EmptySubcommands,
    },
)

StackOpsSubcommands = TypedDict(
    "StackOpsSubcommands",
    {
        "devops": StackOpsDevopsCommand,
        "cloud": StackOpsCloudCommand,
        "terminal": StackOpsTerminalCommand,
        "agents": StackOpsAgentsCommand,
        "utils": StackOpsUtilsCommand,
        "seek": StackOpsSeekCommand,
        "fire": StackOpsFireCommand,
        "preview": StackOpsPreviewCommand,
    },
)

StackOpsCommandHierarchy = TypedDict(
    "StackOpsCommandHierarchy",
    {
        "command_name": Literal["stackops"],
        "short_name": Literal[None],
        "help": Literal["StackOps CLI - Manage your machine configurations and workflows"],
        "subcommands": StackOpsSubcommands,
    },
)
