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
        "help": Literal["📝 <r> Register a new backup entry in user mapper_data.yaml."],
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
        "help": Literal["🔎 <s> Search CLI graph entries and run the selected command help."],
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

StackOpsCroshellCommand = TypedDict(
    "StackOpsCroshellCommand",
    {
        "command_name": Literal["croshell"],
        "short_name": Literal["r"],
        "help": Literal["<r> Cross-shell command execution"],
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
        "croshell": StackOpsCroshellCommand,
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

STACKOPS_DEVOPS_INSTALL_COMMAND: StackOpsDevopsInstallCommand = {
    "command_name": "install",
    "short_name": "i",
    "help": "🔧 <i> Install essential packages",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_SYNC_COMMAND: StackOpsDevopsReposSyncCommand = {
    "command_name": "sync",
    "short_name": "s",
    "help": "📥 <s> Clone repositories described by a repos.json specification",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_REGISTER_COMMAND: StackOpsDevopsReposRegisterCommand = {
    "command_name": "register",
    "short_name": "r",
    "help": "📝 <r> Record repositories into a repos.json specification",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_CHECKOUT_TO_COMMIT_COMMAND: StackOpsDevopsReposCheckoutToCommitCommand = {
    "command_name": "checkout-to-commit",
    "short_name": "ctc",
    "help": "🔀 [ctc] Deprecated: use sync --checkout-to-commit",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_CHECKOUT_TO_BRANCH_COMMAND: StackOpsDevopsReposCheckoutToBranchCommand = {
    "command_name": "checkout-to-branch",
    "short_name": "ctb",
    "help": "🔀 [ctb] Deprecated: use sync --checkout-to-branch",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_ACTION_COMMAND: StackOpsDevopsReposActionCommand = {
    "command_name": "action",
    "short_name": "a",
    "help": "🔄 <a> Run pull/commit/push actions across repositories",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_ANALYZE_COMMAND: StackOpsDevopsReposAnalyzeCommand = {
    "command_name": "analyze",
    "short_name": "z",
    "help": "📊 <z> Analyze repository development over time",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_GUARD_COMMAND: StackOpsDevopsReposGuardCommand = {
    "command_name": "guard",
    "short_name": "g",
    "help": "🔐 <g> Securely sync git repository to/from cloud with encryption",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_VIZ_COMMAND: StackOpsDevopsReposVizCommand = {
    "command_name": "viz",
    "short_name": "v",
    "help": "🎬 <v> Visualize repository activity using Gource",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_COUNT_LINES_COMMAND: StackOpsDevopsReposCountLinesCommand = {
    "command_name": "count-lines",
    "short_name": "lc",
    "help": "📄 <l> Count python lines of code in current repo + historical edits.",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_CONFIG_LINTERS_COMMAND: StackOpsDevopsReposConfigLintersCommand = {
    "command_name": "config-linters",
    "short_name": "l",
    "help": "🧰 <l> Add linter config files to a git repository",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_CLEANUP_COMMAND: StackOpsDevopsReposCleanupCommand = {
    "command_name": "cleanup",
    "short_name": "n",
    "help": "🧹 <n> Clean repository directories from cache files",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_SUBCOMMANDS: StackOpsDevopsReposSubcommands = {
    "sync": STACKOPS_DEVOPS_REPOS_SYNC_COMMAND,
    "register": STACKOPS_DEVOPS_REPOS_REGISTER_COMMAND,
    "checkout-to-commit": STACKOPS_DEVOPS_REPOS_CHECKOUT_TO_COMMIT_COMMAND,
    "checkout-to-branch": STACKOPS_DEVOPS_REPOS_CHECKOUT_TO_BRANCH_COMMAND,
    "action": STACKOPS_DEVOPS_REPOS_ACTION_COMMAND,
    "analyze": STACKOPS_DEVOPS_REPOS_ANALYZE_COMMAND,
    "guard": STACKOPS_DEVOPS_REPOS_GUARD_COMMAND,
    "viz": STACKOPS_DEVOPS_REPOS_VIZ_COMMAND,
    "count-lines": STACKOPS_DEVOPS_REPOS_COUNT_LINES_COMMAND,
    "config-linters": STACKOPS_DEVOPS_REPOS_CONFIG_LINTERS_COMMAND,
    "cleanup": STACKOPS_DEVOPS_REPOS_CLEANUP_COMMAND,
}

STACKOPS_DEVOPS_REPOS_COMMAND: StackOpsDevopsReposCommand = {
    "command_name": "repos",
    "short_name": "r",
    "help": "📁 <r> Manage development repositories",
    "subcommands": STACKOPS_DEVOPS_REPOS_SUBCOMMANDS,
}

STACKOPS_DEVOPS_CONFIG_SYNC_COMMAND: StackOpsDevopsConfigSyncCommand = {
    "command_name": "sync",
    "short_name": "s",
    "help": "🔄 <s> Sync dotfiles.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_REGISTER_COMMAND: StackOpsDevopsConfigRegisterCommand = {
    "command_name": "register",
    "short_name": "r",
    "help": "📇 <r> Register dotfiles against user mapper.yaml",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_EDIT_COMMAND: StackOpsDevopsConfigEditCommand = {
    "command_name": "edit",
    "short_name": "e",
    "help": "📝 <e> Open dotfiles mapper.yaml in nano, hx, or code.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_EXPORT_DOTFILES_COMMAND: StackOpsDevopsConfigExportDotfilesCommand = {
    "command_name": "export-dotfiles",
    "short_name": "E",
    "help": "📤 <E> Export dotfiles for migration to new machine.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_IMPORT_DOTFILES_COMMAND: StackOpsDevopsConfigImportDotfilesCommand = {
    "command_name": "import-dotfiles",
    "short_name": "I",
    "help": "📥 <I> Import dotfiles from exported archive.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_CONFIG_SHELL_COMMAND: StackOpsDevopsConfigTerminalConfigShellCommand = {
    "command_name": "config-shell",
    "short_name": "s",
    "help": "🐚 <s> Create or configure a shell profile.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_STARSHIP_THEME_COMMAND: StackOpsDevopsConfigTerminalStarshipThemeCommand = {
    "command_name": "starship-theme",
    "short_name": "t",
    "help": "⭐ <t> Select starship prompt theme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_PWSH_THEME_COMMAND: StackOpsDevopsConfigTerminalPwshThemeCommand = {
    "command_name": "pwsh-theme",
    "short_name": "T",
    "help": "⚡ <T> Select powershell prompt theme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_WEZTERM_THEME_COMMAND: StackOpsDevopsConfigTerminalWeztermThemeCommand = {
    "command_name": "wezterm-theme",
    "short_name": "W",
    "help": "💻 <W> Select WezTerm terminal theme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_GHOSTTY_THEME_COMMAND: StackOpsDevopsConfigTerminalGhosttyThemeCommand = {
    "command_name": "ghostty-theme",
    "short_name": "g",
    "help": "👻 <g> Select Ghostty terminal theme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_WINDOWS_TERMINAL_THEME_COMMAND: StackOpsDevopsConfigTerminalWindowsTerminalThemeCommand = {
    "command_name": "windows-terminal-theme",
    "short_name": "x",
    "help": "🪟 <x> Select Windows Terminal color scheme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_SUBCOMMANDS: StackOpsDevopsConfigTerminalSubcommands = {
    "config-shell": STACKOPS_DEVOPS_CONFIG_TERMINAL_CONFIG_SHELL_COMMAND,
    "starship-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_STARSHIP_THEME_COMMAND,
    "pwsh-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_PWSH_THEME_COMMAND,
    "wezterm-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_WEZTERM_THEME_COMMAND,
    "ghostty-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_GHOSTTY_THEME_COMMAND,
    "windows-terminal-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_WINDOWS_TERMINAL_THEME_COMMAND,
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_COMMAND: StackOpsDevopsConfigTerminalCommand = {
    "command_name": "terminal",
    "short_name": "t",
    "help": "🐚 <t> Configure your terminal profile.",
    "subcommands": STACKOPS_DEVOPS_CONFIG_TERMINAL_SUBCOMMANDS,
}

STACKOPS_DEVOPS_CONFIG_INTERACTIVE_COMMAND: StackOpsDevopsConfigInteractiveCommand = {
    "command_name": "interactive",
    "short_name": "i",
    "help": "🤖 <i> Interactive configuration of machine.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_COPY_ASSETS_COMMAND: StackOpsDevopsConfigCopyAssetsCommand = {
    "command_name": "copy-assets",
    "short_name": "c",
    "help": "📋 <c> Copy asset files from library to machine.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_DUMP_COMMAND: StackOpsDevopsConfigDumpCommand = {
    "command_name": "dump",
    "short_name": "d",
    "help": "📦 <d> Dump example configuration files and init scripts.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_SUBCOMMANDS: StackOpsDevopsConfigSubcommands = {
    "sync": STACKOPS_DEVOPS_CONFIG_SYNC_COMMAND,
    "register": STACKOPS_DEVOPS_CONFIG_REGISTER_COMMAND,
    "edit": STACKOPS_DEVOPS_CONFIG_EDIT_COMMAND,
    "export-dotfiles": STACKOPS_DEVOPS_CONFIG_EXPORT_DOTFILES_COMMAND,
    "import-dotfiles": STACKOPS_DEVOPS_CONFIG_IMPORT_DOTFILES_COMMAND,
    "terminal": STACKOPS_DEVOPS_CONFIG_TERMINAL_COMMAND,
    "interactive": STACKOPS_DEVOPS_CONFIG_INTERACTIVE_COMMAND,
    "copy-assets": STACKOPS_DEVOPS_CONFIG_COPY_ASSETS_COMMAND,
    "dump": STACKOPS_DEVOPS_CONFIG_DUMP_COMMAND,
}

STACKOPS_DEVOPS_CONFIG_COMMAND: StackOpsDevopsConfigCommand = {
    "command_name": "config",
    "short_name": "c",
    "help": "🔩 <c> Configuration management",
    "subcommands": STACKOPS_DEVOPS_CONFIG_SUBCOMMANDS,
}

STACKOPS_DEVOPS_DATA_SYNC_COMMAND: StackOpsDevopsDataSyncCommand = {
    "command_name": "sync",
    "short_name": "s",
    "help": "🔄 <s> Back up or retrieve files and directories using rclone.",
    "subcommands": {},
}

STACKOPS_DEVOPS_DATA_REGISTER_COMMAND: StackOpsDevopsDataRegisterCommand = {
    "command_name": "register",
    "short_name": "r",
    "help": "📝 <r> Register a new backup entry in user mapper_data.yaml.",
    "subcommands": {},
}

STACKOPS_DEVOPS_DATA_EDIT_COMMAND: StackOpsDevopsDataEditCommand = {
    "command_name": "edit",
    "short_name": "e",
    "help": "✏️ <e> Open backup configuration file in nano, hx, or code.",
    "subcommands": {},
}

STACKOPS_DEVOPS_DATA_SUBCOMMANDS: StackOpsDevopsDataSubcommands = {
    "sync": STACKOPS_DEVOPS_DATA_SYNC_COMMAND,
    "register": STACKOPS_DEVOPS_DATA_REGISTER_COMMAND,
    "edit": STACKOPS_DEVOPS_DATA_EDIT_COMMAND,
}

STACKOPS_DEVOPS_DATA_COMMAND: StackOpsDevopsDataCommand = {
    "command_name": "data",
    "short_name": "d",
    "help": "💾 <d> Data management",
    "subcommands": STACKOPS_DEVOPS_DATA_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_INSTALL_COMMAND: StackOpsDevopsSelfInstallCommand = {
    "command_name": "install",
    "short_name": "i",
    "help": "📋 <i> install stackops locally for nightly updates.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_UPDATE_COMMAND: StackOpsDevopsSelfUpdateCommand = {
    "command_name": "update",
    "short_name": "u",
    "help": "🔄 <u> UPDATE stackops",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_STATUS_COMMAND: StackOpsDevopsSelfStatusCommand = {
    "command_name": "status",
    "short_name": "s",
    "help": "📊 <s> STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_SCAN_COMMAND: StackOpsDevopsSelfSecurityScanCommand = {
    "command_name": "scan",
    "short_name": "s",
    "help": "<s> Scan installed apps or a single file path with VirusTotal",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_LIST_COMMAND: StackOpsDevopsSelfSecurityListCommand = {
    "command_name": "list",
    "short_name": "l",
    "help": "<l> List installed apps, optionally filtered by comma-separated app names",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_UPLOAD_COMMAND: StackOpsDevopsSelfSecurityUploadCommand = {
    "command_name": "upload",
    "short_name": "u",
    "help": "<u> Upload a local file to cloud storage",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_DOWNLOAD_COMMAND: StackOpsDevopsSelfSecurityDownloadCommand = {
    "command_name": "download",
    "short_name": "d",
    "help": "<d> Download a file from Google Drive",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_INSTALL_COMMAND: StackOpsDevopsSelfSecurityInstallCommand = {
    "command_name": "install",
    "short_name": "i",
    "help": "<i> Install safe apps from app metadata report",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_REPORT_COMMAND: StackOpsDevopsSelfSecurityReportCommand = {
    "command_name": "report",
    "short_name": "r",
    "help": "<r> Show the full saved scan report by default, or CSV rows/summary stats",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_SUBCOMMANDS: StackOpsDevopsSelfSecuritySubcommands = {
    "scan": STACKOPS_DEVOPS_SELF_SECURITY_SCAN_COMMAND,
    "list": STACKOPS_DEVOPS_SELF_SECURITY_LIST_COMMAND,
    "upload": STACKOPS_DEVOPS_SELF_SECURITY_UPLOAD_COMMAND,
    "download": STACKOPS_DEVOPS_SELF_SECURITY_DOWNLOAD_COMMAND,
    "install": STACKOPS_DEVOPS_SELF_SECURITY_INSTALL_COMMAND,
    "report": STACKOPS_DEVOPS_SELF_SECURITY_REPORT_COMMAND,
}

STACKOPS_DEVOPS_SELF_SECURITY_COMMAND: StackOpsDevopsSelfSecurityCommand = {
    "command_name": "security",
    "short_name": "y",
    "help": "🔐 <y> Security related CLI tools.",
    "subcommands": STACKOPS_DEVOPS_SELF_SECURITY_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_EXPLORE_SEARCH_COMMAND: StackOpsDevopsSelfExploreSearchCommand = {
    "command_name": "search",
    "short_name": "s",
    "help": "🔎 <s> Search CLI graph entries and run the selected command help.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_TREE_COMMAND: StackOpsDevopsSelfExploreTreeCommand = {
    "command_name": "tree",
    "short_name": "t",
    "help": "🌳 <t> Render a rich tree view in the terminal.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_DOT_COMMAND: StackOpsDevopsSelfExploreDotCommand = {
    "command_name": "dot",
    "short_name": "d",
    "help": "🧩 <d> Export the graph as Graphviz DOT.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_VIEW_COMMAND: StackOpsDevopsSelfExploreViewCommand = {
    "command_name": "view",
    "short_name": "v",
    "help": "📊 <v> Render a Plotly hierarchy chart.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_TUI_COMMAND: StackOpsDevopsSelfExploreTuiCommand = {
    "command_name": "tui",
    "short_name": "u",
    "help": "📚 <u> NAVIGATE command structure with TUI",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_SUBCOMMANDS: StackOpsDevopsSelfExploreSubcommands = {
    "search": STACKOPS_DEVOPS_SELF_EXPLORE_SEARCH_COMMAND,
    "tree": STACKOPS_DEVOPS_SELF_EXPLORE_TREE_COMMAND,
    "dot": STACKOPS_DEVOPS_SELF_EXPLORE_DOT_COMMAND,
    "view": STACKOPS_DEVOPS_SELF_EXPLORE_VIEW_COMMAND,
    "tui": STACKOPS_DEVOPS_SELF_EXPLORE_TUI_COMMAND,
}

STACKOPS_DEVOPS_SELF_EXPLORE_COMMAND: StackOpsDevopsSelfExploreCommand = {
    "command_name": "explore",
    "short_name": "x",
    "help": "🧭 <x> Explore the StackOps CLI graph.",
    "subcommands": STACKOPS_DEVOPS_SELF_EXPLORE_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_README_COMMAND: StackOpsDevopsSelfReadmeCommand = {
    "command_name": "readme",
    "short_name": "r",
    "help": "📚 <r> render readme markdown in terminal.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_DOCS_COMMAND: StackOpsDevopsSelfDocsCommand = {
    "command_name": "docs",
    "short_name": "o",
    "help": "📚 <o> Serve local docs with preview URLs.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_INSTALLER_COMMAND: StackOpsDevopsSelfBuildInstallerCommand = {
    "command_name": "build-installer",
    "short_name": "e",
    "help": "📤 <e> Build an offline installer.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_DOCKER_COMMAND: StackOpsDevopsSelfBuildDockerCommand = {
    "command_name": "build-docker",
    "short_name": "d",
    "help": "🧱 <d> Build docker images (wraps jobs/shell/docker_build_and_publish.sh)",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_ASSETS_UPDATE_CLI_GRAPH_COMMAND: StackOpsDevopsSelfBuildAssetsUpdateCLIGraphCommand = {
    "command_name": "update-cli-graph",
    "short_name": "g",
    "help": "🧩 <g> Regenerate the checked-in CLI graph snapshot.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_ASSETS_REGENERATE_CHARTS_COMMAND: StackOpsDevopsSelfBuildAssetsRegenerateChartsCommand = {
    "command_name": "regenerate-charts",
    "short_name": "c",
    "help": "☀ <c> Regenerate the checked-in sunburst HTML chart.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_ASSETS_SUBCOMMANDS: StackOpsDevopsSelfBuildAssetsSubcommands = {
    "update-cli-graph": STACKOPS_DEVOPS_SELF_BUILD_ASSETS_UPDATE_CLI_GRAPH_COMMAND,
    "regenerate-charts": STACKOPS_DEVOPS_SELF_BUILD_ASSETS_REGENERATE_CHARTS_COMMAND,
}

STACKOPS_DEVOPS_SELF_BUILD_ASSETS_COMMAND: StackOpsDevopsSelfBuildAssetsCommand = {
    "command_name": "build-assets",
    "short_name": "a",
    "help": "🗂 <a> Regenerate repo-local CLI graph assets.",
    "subcommands": STACKOPS_DEVOPS_SELF_BUILD_ASSETS_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_WORKFLOWS_UPDATE_INSTALLER_COMMAND: StackOpsDevopsSelfWorkflowsUpdateInstallerCommand = {
    "command_name": "update-installer",
    "short_name": "u",
    "help": "🔄 <u> Create an agents layout for updating installer_data.json.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_WORKFLOWS_UPDATE_TEST_COMMAND: StackOpsDevopsSelfWorkflowsUpdateTestCommand = {
    "command_name": "update-test",
    "short_name": "t",
    "help": "🧪 <t> Create an agents layout for writing tests from repo Python sources.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_WORKFLOWS_UPDATE_DOCS_COMMAND: StackOpsDevopsSelfWorkflowsUpdateDocsCommand = {
    "command_name": "update-docs",
    "short_name": "d",
    "help": "📚 <d> Create an agents layout for updating CLI and API docs only.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_WORKFLOWS_UPDATE_LOGIC_COMMAND: StackOpsDevopsSelfWorkflowsUpdateLogicCommand = {
    "command_name": "update-logic",
    "short_name": "l",
    "help": "🧠 <l> Create an agents layout for checking CLI command logic.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_WORKFLOWS_SUBCOMMANDS: StackOpsDevopsSelfWorkflowsSubcommands = {
    "update-installer": STACKOPS_DEVOPS_SELF_WORKFLOWS_UPDATE_INSTALLER_COMMAND,
    "update-test": STACKOPS_DEVOPS_SELF_WORKFLOWS_UPDATE_TEST_COMMAND,
    "update-docs": STACKOPS_DEVOPS_SELF_WORKFLOWS_UPDATE_DOCS_COMMAND,
    "update-logic": STACKOPS_DEVOPS_SELF_WORKFLOWS_UPDATE_LOGIC_COMMAND,
}

STACKOPS_DEVOPS_SELF_WORKFLOWS_COMMAND: StackOpsDevopsSelfWorkflowsCommand = {
    "command_name": "workflows",
    "short_name": "w",
    "help": "🤖 <w> Developer AI workflows.",
    "subcommands": STACKOPS_DEVOPS_SELF_WORKFLOWS_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_SUBCOMMANDS: StackOpsDevopsSelfSubcommands = {
    "install": STACKOPS_DEVOPS_SELF_INSTALL_COMMAND,
    "update": STACKOPS_DEVOPS_SELF_UPDATE_COMMAND,
    "status": STACKOPS_DEVOPS_SELF_STATUS_COMMAND,
    "security": STACKOPS_DEVOPS_SELF_SECURITY_COMMAND,
    "explore": STACKOPS_DEVOPS_SELF_EXPLORE_COMMAND,
    "readme": STACKOPS_DEVOPS_SELF_README_COMMAND,
    "docs": STACKOPS_DEVOPS_SELF_DOCS_COMMAND,
    "build-installer": STACKOPS_DEVOPS_SELF_BUILD_INSTALLER_COMMAND,
    "build-docker": STACKOPS_DEVOPS_SELF_BUILD_DOCKER_COMMAND,
    "build-assets": STACKOPS_DEVOPS_SELF_BUILD_ASSETS_COMMAND,
    "workflows": STACKOPS_DEVOPS_SELF_WORKFLOWS_COMMAND,
}

STACKOPS_DEVOPS_SELF_COMMAND: StackOpsDevopsSelfCommand = {
    "command_name": "self",
    "short_name": "s",
    "help": "🔧 <s> Self management",
    "subcommands": STACKOPS_DEVOPS_SELF_SUBCOMMANDS,
}

STACKOPS_DEVOPS_NETWORK_SHARE_TERMINAL_COMMAND: StackOpsDevopsNetworkShareTerminalCommand = {
    "command_name": "share-terminal",
    "short_name": "t",
    "help": "📡 <t> Share terminal via web browser",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SHARE_SERVER_COMMAND: StackOpsDevopsNetworkShareServerCommand = {
    "command_name": "share-server",
    "short_name": "s",
    "help": "🌐 <s> Start local/global server to share files/folders via web browser",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SEND_COMMAND: StackOpsDevopsNetworkSendCommand = {
    "command_name": "send",
    "short_name": "sx",
    "help": "📁 <sx> send files from here.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_RECEIVE_COMMAND: StackOpsDevopsNetworkReceiveCommand = {
    "command_name": "receive",
    "short_name": "rx",
    "help": "📁 <rx> receive files to here.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SHARE_TEMP_FILE_COMMAND: StackOpsDevopsNetworkShareTempFileCommand = {
    "command_name": "share-temp-file",
    "short_name": "T",
    "help": "🌡 <T> Share a file via temp.sh",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_INSTALL_SERVER_COMMAND: StackOpsDevopsNetworkSSHInstallServerCommand = {
    "command_name": "install-server",
    "short_name": "i",
    "help": "📡 <i> Install SSH server",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_CHANGE_PORT_COMMAND: StackOpsDevopsNetworkSSHChangePortCommand = {
    "command_name": "change-port",
    "short_name": "p",
    "help": "🔌 <p> Change SSH port (Linux/WSL only)",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_ADD_KEY_COMMAND: StackOpsDevopsNetworkSSHAddKeyCommand = {
    "command_name": "add-key",
    "short_name": "k",
    "help": "🔑 <k> Add SSH public key to this machine",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_DEBUG_COMMAND: StackOpsDevopsNetworkSSHDebugCommand = {
    "command_name": "debug",
    "short_name": "d",
    "help": "🐛 <d> Debug SSH connection",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_SUBCOMMANDS: StackOpsDevopsNetworkSSHSubcommands = {
    "install-server": STACKOPS_DEVOPS_NETWORK_SSH_INSTALL_SERVER_COMMAND,
    "change-port": STACKOPS_DEVOPS_NETWORK_SSH_CHANGE_PORT_COMMAND,
    "add-key": STACKOPS_DEVOPS_NETWORK_SSH_ADD_KEY_COMMAND,
    "debug": STACKOPS_DEVOPS_NETWORK_SSH_DEBUG_COMMAND,
}

STACKOPS_DEVOPS_NETWORK_SSH_COMMAND: StackOpsDevopsNetworkSSHCommand = {
    "command_name": "ssh",
    "short_name": "S",
    "help": "🔐 <S> SSH subcommands",
    "subcommands": STACKOPS_DEVOPS_NETWORK_SSH_SUBCOMMANDS,
}

STACKOPS_DEVOPS_NETWORK_DEVICE_SWITCH_PUBLIC_IP_COMMAND: StackOpsDevopsNetworkDeviceSwitchPublicIpCommand = {
    "command_name": "switch-public-ip",
    "short_name": "s",
    "help": "🔁 <s> Switch public IP address (Cloudflare WARP)",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_WIFI_SELECT_COMMAND: StackOpsDevopsNetworkDeviceWifiSelectCommand = {
    "command_name": "wifi-select",
    "short_name": "w",
    "help": "📶 <w> WiFi connection utility.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_BIND_WSL_PORT_COMMAND: StackOpsDevopsNetworkDeviceBindWSLPortCommand = {
    "command_name": "bind-wsl-port",
    "short_name": "b",
    "help": "🔌 <b> Bind WSL port to Windows host",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_OPEN_WSL_PORT_COMMAND: StackOpsDevopsNetworkDeviceOpenWSLPortCommand = {
    "command_name": "open-wsl-port",
    "short_name": "o",
    "help": "🔥 <o> Open Windows firewall ports for WSL.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_LINK_WSL_WINDOWS_COMMAND: StackOpsDevopsNetworkDeviceLinkWSLWindowsCommand = {
    "command_name": "link-wsl-windows",
    "short_name": "l",
    "help": "🔗 <l> Link WSL home and Windows home directories.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_RESET_CLOUDFLARE_TUNNEL_COMMAND: StackOpsDevopsNetworkDeviceResetCloudflareTunnelCommand = {
    "command_name": "reset-cloudflare-tunnel",
    "short_name": "r",
    "help": "☁ <r> Reset Cloudflare tunnel service",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_ADD_IP_EXCLUSION_TO_WARP_COMMAND: StackOpsDevopsNetworkDeviceAddIpExclusionToWarpCommand = {
    "command_name": "add-ip-exclusion-to-warp",
    "short_name": "p",
    "help": "🚫 <p> Add IP exclusion to WARP",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_SUBCOMMANDS: StackOpsDevopsNetworkDeviceSubcommands = {
    "switch-public-ip": STACKOPS_DEVOPS_NETWORK_DEVICE_SWITCH_PUBLIC_IP_COMMAND,
    "wifi-select": STACKOPS_DEVOPS_NETWORK_DEVICE_WIFI_SELECT_COMMAND,
    "bind-wsl-port": STACKOPS_DEVOPS_NETWORK_DEVICE_BIND_WSL_PORT_COMMAND,
    "open-wsl-port": STACKOPS_DEVOPS_NETWORK_DEVICE_OPEN_WSL_PORT_COMMAND,
    "link-wsl-windows": STACKOPS_DEVOPS_NETWORK_DEVICE_LINK_WSL_WINDOWS_COMMAND,
    "reset-cloudflare-tunnel": STACKOPS_DEVOPS_NETWORK_DEVICE_RESET_CLOUDFLARE_TUNNEL_COMMAND,
    "add-ip-exclusion-to-warp": STACKOPS_DEVOPS_NETWORK_DEVICE_ADD_IP_EXCLUSION_TO_WARP_COMMAND,
}

STACKOPS_DEVOPS_NETWORK_DEVICE_COMMAND: StackOpsDevopsNetworkDeviceCommand = {
    "command_name": "device",
    "short_name": "d",
    "help": "🖥 <d> Device subcommands",
    "subcommands": STACKOPS_DEVOPS_NETWORK_DEVICE_SUBCOMMANDS,
}

STACKOPS_DEVOPS_NETWORK_SHOW_ADDRESS_COMMAND: StackOpsDevopsNetworkShowAddressCommand = {
    "command_name": "show-address",
    "short_name": "a",
    "help": "📌 <a> Show this computer addresses on network",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_VSCODE_SHARE_COMMAND: StackOpsDevopsNetworkVscodeShareCommand = {
    "command_name": "vscode-share",
    "short_name": "v",
    "help": "💻 <v> Share workspace via VS Code Tunnels",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SUBCOMMANDS: StackOpsDevopsNetworkSubcommands = {
    "share-terminal": STACKOPS_DEVOPS_NETWORK_SHARE_TERMINAL_COMMAND,
    "share-server": STACKOPS_DEVOPS_NETWORK_SHARE_SERVER_COMMAND,
    "send": STACKOPS_DEVOPS_NETWORK_SEND_COMMAND,
    "receive": STACKOPS_DEVOPS_NETWORK_RECEIVE_COMMAND,
    "share-temp-file": STACKOPS_DEVOPS_NETWORK_SHARE_TEMP_FILE_COMMAND,
    "ssh": STACKOPS_DEVOPS_NETWORK_SSH_COMMAND,
    "device": STACKOPS_DEVOPS_NETWORK_DEVICE_COMMAND,
    "show-address": STACKOPS_DEVOPS_NETWORK_SHOW_ADDRESS_COMMAND,
    "vscode-share": STACKOPS_DEVOPS_NETWORK_VSCODE_SHARE_COMMAND,
}

STACKOPS_DEVOPS_NETWORK_COMMAND: StackOpsDevopsNetworkCommand = {
    "command_name": "network",
    "short_name": "n",
    "help": "🌐 <n> Network management",
    "subcommands": STACKOPS_DEVOPS_NETWORK_SUBCOMMANDS,
}

STACKOPS_DEVOPS_EXECUTE_COMMAND: StackOpsDevopsExecuteCommand = {
    "command_name": "execute",
    "short_name": "e",
    "help": "🚀 <e> Execute python/shell scripts from pre-defined directories or as command",
    "subcommands": {},
}

STACKOPS_DEVOPS_SUBCOMMANDS: StackOpsDevopsSubcommands = {
    "install": STACKOPS_DEVOPS_INSTALL_COMMAND,
    "repos": STACKOPS_DEVOPS_REPOS_COMMAND,
    "config": STACKOPS_DEVOPS_CONFIG_COMMAND,
    "data": STACKOPS_DEVOPS_DATA_COMMAND,
    "self": STACKOPS_DEVOPS_SELF_COMMAND,
    "network": STACKOPS_DEVOPS_NETWORK_COMMAND,
    "execute": STACKOPS_DEVOPS_EXECUTE_COMMAND,
}

STACKOPS_DEVOPS_COMMAND: StackOpsDevopsCommand = {
    "command_name": "devops",
    "short_name": "d",
    "help": "<d> DevOps related commands",
    "subcommands": STACKOPS_DEVOPS_SUBCOMMANDS,
}

STACKOPS_CLOUD_SYNC_COMMAND: StackOpsCloudSyncCommand = {
    "command_name": "sync",
    "short_name": "s",
    "help": "🔄 <s> Synchronize files/folders between local and cloud storage.",
    "subcommands": {},
}

STACKOPS_CLOUD_COPY_COMMAND: StackOpsCloudCopyCommand = {
    "command_name": "copy",
    "short_name": "c",
    "help": "📤 <c> Upload or 📥 Download files/folders to/from cloud storage.",
    "subcommands": {},
}

STACKOPS_CLOUD_MOUNT_COMMAND: StackOpsCloudMountCommand = {
    "command_name": "mount",
    "short_name": "m",
    "help": "🔗 <m> Mount cloud storage services as local drives.",
    "subcommands": {},
}

STACKOPS_CLOUD_FTPX_COMMAND: StackOpsCloudFtpxCommand = {
    "command_name": "ftpx",
    "short_name": "f",
    "help": "📦 <f> File transfer utility through SSH.",
    "subcommands": {},
}

STACKOPS_CLOUD_SUBCOMMANDS: StackOpsCloudSubcommands = {
    "sync": STACKOPS_CLOUD_SYNC_COMMAND,
    "copy": STACKOPS_CLOUD_COPY_COMMAND,
    "mount": STACKOPS_CLOUD_MOUNT_COMMAND,
    "ftpx": STACKOPS_CLOUD_FTPX_COMMAND,
}

STACKOPS_CLOUD_COMMAND: StackOpsCloudCommand = {
    "command_name": "cloud",
    "short_name": "c",
    "help": "<c> Cloud management commands",
    "subcommands": STACKOPS_CLOUD_SUBCOMMANDS,
}

STACKOPS_TERMINAL_RUN_COMMAND: StackOpsTerminalRunCommand = {
    "command_name": "run",
    "short_name": "r",
    "help": "<r> Run the selected layout(s)",
    "subcommands": {},
}

STACKOPS_TERMINAL_RUN_ALL_COMMAND: StackOpsTerminalRunAllCommand = {
    "command_name": "run-all",
    "short_name": "R",
    "help": "<R> Dynamically run every layout in a file",
    "subcommands": {},
}

STACKOPS_TERMINAL_RUN_AOE_COMMAND: StackOpsTerminalRunAoeCommand = {
    "command_name": "run-aoe",
    "short_name": "e",
    "help": "<e> Run selected layout(s) through agent-of-empires",
    "subcommands": {},
}

STACKOPS_TERMINAL_ATTACH_COMMAND: StackOpsTerminalAttachCommand = {
    "command_name": "attach",
    "short_name": "a",
    "help": "<a> Attach to a session target",
    "subcommands": {},
}

STACKOPS_TERMINAL_KILL_COMMAND: StackOpsTerminalKillCommand = {
    "command_name": "kill",
    "short_name": "k",
    "help": "<k> Kill a session target",
    "subcommands": {},
}

STACKOPS_TERMINAL_TRACE_COMMAND: StackOpsTerminalTraceCommand = {
    "command_name": "trace",
    "short_name": "t",
    "help": "<t> Trace a tmux session until it settles",
    "subcommands": {},
}

STACKOPS_TERMINAL_CREATE_FROM_FUNCTION_COMMAND: StackOpsTerminalCreateFromFunctionCommand = {
    "command_name": "create-from-function",
    "short_name": "c",
    "help": "<c> Create a layout from a function",
    "subcommands": {},
}

STACKOPS_TERMINAL_BALANCE_LOAD_COMMAND: StackOpsTerminalBalanceLoadCommand = {
    "command_name": "balance-load",
    "short_name": "b",
    "help": "<b> Balance the load across sessions",
    "subcommands": {},
}

STACKOPS_TERMINAL_CREATE_TEMPLATE_COMMAND: StackOpsTerminalCreateTemplateCommand = {
    "command_name": "create-template",
    "short_name": "p",
    "help": "<p> Create a layout template file",
    "subcommands": {},
}

STACKOPS_TERMINAL_SUMMARIZE_COMMAND: StackOpsTerminalSummarizeCommand = {
    "command_name": "summarize",
    "short_name": "s",
    "help": "<s> Summarize a layout file",
    "subcommands": {},
}

STACKOPS_TERMINAL_SUBCOMMANDS: StackOpsTerminalSubcommands = {
    "run": STACKOPS_TERMINAL_RUN_COMMAND,
    "run-all": STACKOPS_TERMINAL_RUN_ALL_COMMAND,
    "run-aoe": STACKOPS_TERMINAL_RUN_AOE_COMMAND,
    "attach": STACKOPS_TERMINAL_ATTACH_COMMAND,
    "kill": STACKOPS_TERMINAL_KILL_COMMAND,
    "trace": STACKOPS_TERMINAL_TRACE_COMMAND,
    "create-from-function": STACKOPS_TERMINAL_CREATE_FROM_FUNCTION_COMMAND,
    "balance-load": STACKOPS_TERMINAL_BALANCE_LOAD_COMMAND,
    "create-template": STACKOPS_TERMINAL_CREATE_TEMPLATE_COMMAND,
    "summarize": STACKOPS_TERMINAL_SUMMARIZE_COMMAND,
}

STACKOPS_TERMINAL_COMMAND: StackOpsTerminalCommand = {
    "command_name": "terminal",
    "short_name": "t",
    "help": "<t> Terminal and layout management",
    "subcommands": STACKOPS_TERMINAL_SUBCOMMANDS,
}

STACKOPS_AGENTS_PARALLEL_CREATE_COMMAND: StackOpsAgentsParallelCreateCommand = {
    "command_name": "create",
    "short_name": "c",
    "help": "<c> Create agents layout file, ready to run.",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_CREATE_CONTEXT_COMMAND: StackOpsAgentsParallelCreateContextCommand = {
    "command_name": "create-context",
    "short_name": "x",
    "help": "<x> Run prompt and ask agent to persist context",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_RUN_PARALLEL_COMMAND: StackOpsAgentsParallelRunParallelCommand = {
    "command_name": "run-parallel",
    "short_name": "r",
    "help": "<r> Run named parallel workflow from YAML",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_COLLECT_COMMAND: StackOpsAgentsParallelCollectCommand = {
    "command_name": "collect",
    "short_name": "T",
    "help": "<T> Collect all agent materials into a single file.",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_MAKE_TEMPLATE_COMMAND: StackOpsAgentsParallelMakeTemplateCommand = {
    "command_name": "make-template",
    "short_name": "p",
    "help": "<p> Create a template for fire agents",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_SUBCOMMANDS: StackOpsAgentsParallelSubcommands = {
    "create": STACKOPS_AGENTS_PARALLEL_CREATE_COMMAND,
    "create-context": STACKOPS_AGENTS_PARALLEL_CREATE_CONTEXT_COMMAND,
    "run-parallel": STACKOPS_AGENTS_PARALLEL_RUN_PARALLEL_COMMAND,
    "collect": STACKOPS_AGENTS_PARALLEL_COLLECT_COMMAND,
    "make-template": STACKOPS_AGENTS_PARALLEL_MAKE_TEMPLATE_COMMAND,
}

STACKOPS_AGENTS_PARALLEL_COMMAND: StackOpsAgentsParallelCommand = {
    "command_name": "parallel",
    "short_name": "p",
    "help": "<p> Parallel agent workflow commands",
    "subcommands": STACKOPS_AGENTS_PARALLEL_SUBCOMMANDS,
}

STACKOPS_AGENTS_BROWSER_INSTALL_TECH_COMMAND: StackOpsAgentsBrowserInstallTechCommand = {
    "command_name": "install-tech",
    "short_name": "i",
    "help": "<i> Install browser automation tech",
    "subcommands": {},
}

STACKOPS_AGENTS_BROWSER_LAUNCH_BROWSER_COMMAND: StackOpsAgentsBrowserLaunchBrowserCommand = {
    "command_name": "launch-browser",
    "short_name": "l",
    "help": "<l> Launch Chrome or Brave for CDP automation",
    "subcommands": {},
}

STACKOPS_AGENTS_BROWSER_SUBCOMMANDS: StackOpsAgentsBrowserSubcommands = {
    "install-tech": STACKOPS_AGENTS_BROWSER_INSTALL_TECH_COMMAND,
    "launch-browser": STACKOPS_AGENTS_BROWSER_LAUNCH_BROWSER_COMMAND,
}

STACKOPS_AGENTS_BROWSER_COMMAND: StackOpsAgentsBrowserCommand = {
    "command_name": "browser",
    "short_name": "b",
    "help": "<b> Browser automation commands",
    "subcommands": STACKOPS_AGENTS_BROWSER_SUBCOMMANDS,
}

STACKOPS_AGENTS_ADD_MCP_COMMAND: StackOpsAgentsAddMcpCommand = {
    "command_name": "add-mcp",
    "short_name": "m",
    "help": "<m> Resolve catalog MCP entries or supported skills",
    "subcommands": {},
}

STACKOPS_AGENTS_ADD_SKILL_COMMAND: StackOpsAgentsAddSkillCommand = {
    "command_name": "add-skill",
    "short_name": "s",
    "help": "<s> Add a skill to an agent",
    "subcommands": {},
}

STACKOPS_AGENTS_ADD_TODO_COMMAND: StackOpsAgentsAddTodoCommand = {
    "command_name": "add-todo",
    "short_name": "d",
    "help": "<d> Generate a markdown file listing all Python files in the repo",
    "subcommands": {},
}

STACKOPS_AGENTS_ADD_SYMLINKS_COMMAND: StackOpsAgentsAddSymlinksCommand = {
    "command_name": "add-symlinks",
    "short_name": "l",
    "help": "<l> Create symlinks to the current repo in ~/code_copies/",
    "subcommands": {},
}

STACKOPS_AGENTS_ADD_CONFIG_COMMAND: StackOpsAgentsAddConfigCommand = {
    "command_name": "add-config",
    "short_name": "g",
    "help": "<g> Initialize AI configurations in the current repository",
    "subcommands": {},
}

STACKOPS_AGENTS_RUN_PROMPT_COMMAND: StackOpsAgentsRunPromptCommand = {
    "command_name": "run-prompt",
    "short_name": "r",
    "help": "<r> Run one prompt via selected agent",
    "subcommands": {},
}

STACKOPS_AGENTS_ASK_COMMAND: StackOpsAgentsAskCommand = {
    "command_name": "ask",
    "short_name": "a",
    "help": "<a> Ask a selected agent directly",
    "subcommands": {},
}

STACKOPS_AGENTS_SUBCOMMANDS: StackOpsAgentsSubcommands = {
    "parallel": STACKOPS_AGENTS_PARALLEL_COMMAND,
    "browser": STACKOPS_AGENTS_BROWSER_COMMAND,
    "add-mcp": STACKOPS_AGENTS_ADD_MCP_COMMAND,
    "add-skill": STACKOPS_AGENTS_ADD_SKILL_COMMAND,
    "add-todo": STACKOPS_AGENTS_ADD_TODO_COMMAND,
    "add-symlinks": STACKOPS_AGENTS_ADD_SYMLINKS_COMMAND,
    "add-config": STACKOPS_AGENTS_ADD_CONFIG_COMMAND,
    "run-prompt": STACKOPS_AGENTS_RUN_PROMPT_COMMAND,
    "ask": STACKOPS_AGENTS_ASK_COMMAND,
}

STACKOPS_AGENTS_COMMAND: StackOpsAgentsCommand = {
    "command_name": "agents",
    "short_name": "a",
    "help": "<a> 🤖 AI Agents management commands",
    "subcommands": STACKOPS_AGENTS_SUBCOMMANDS,
}

STACKOPS_UTILS_MACHINE_KILL_PROCESS_COMMAND: StackOpsUtilsMachineKillProcessCommand = {
    "command_name": "kill-process",
    "short_name": "k",
    "help": "⚔ <k> Choose a process to kill",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_ENVIRONMENT_COMMAND: StackOpsUtilsMachineEnvironmentCommand = {
    "command_name": "environment",
    "short_name": "v",
    "help": "⌘ <v> Navigate ENV/PATH variables. Default: fuzzy picker with preview; use --tui for Textual.",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_GET_MACHINE_SPECS_COMMAND: StackOpsUtilsMachineGetMachineSpecsCommand = {
    "command_name": "get-machine-specs",
    "short_name": "s",
    "help": "🖥 <s> Get machine specifications.",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_LIST_DEVICES_COMMAND: StackOpsUtilsMachineListDevicesCommand = {
    "command_name": "list-devices",
    "short_name": "l",
    "help": "💽 <l> List available devices for mounting.",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_MOUNT_COMMAND: StackOpsUtilsMachineMountCommand = {
    "command_name": "mount",
    "short_name": "m",
    "help": "🔌 <m> Mount a device to a mount point.",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_SUBCOMMANDS: StackOpsUtilsMachineSubcommands = {
    "kill-process": STACKOPS_UTILS_MACHINE_KILL_PROCESS_COMMAND,
    "environment": STACKOPS_UTILS_MACHINE_ENVIRONMENT_COMMAND,
    "get-machine-specs": STACKOPS_UTILS_MACHINE_GET_MACHINE_SPECS_COMMAND,
    "list-devices": STACKOPS_UTILS_MACHINE_LIST_DEVICES_COMMAND,
    "mount": STACKOPS_UTILS_MACHINE_MOUNT_COMMAND,
}

STACKOPS_UTILS_MACHINE_COMMAND: StackOpsUtilsMachineCommand = {
    "command_name": "machine",
    "short_name": "m",
    "help": "🖥 <m> Machine and device utilities",
    "subcommands": STACKOPS_UTILS_MACHINE_SUBCOMMANDS,
}

STACKOPS_UTILS_PYPROJECT_INIT_PROJECT_COMMAND: StackOpsUtilsPyprojectInitProjectCommand = {
    "command_name": "init-project",
    "short_name": "i",
    "help": "✦ <i> Initialize a project with a uv virtual environment and install dev packages.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_UPGRADE_PACKAGES_COMMAND: StackOpsUtilsPyprojectUpgradePackagesCommand = {
    "command_name": "upgrade-packages",
    "short_name": "a",
    "help": "↑ <a> Upgrade project dependencies.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TYPE_HINT_COMMAND: StackOpsUtilsPyprojectTypeHintCommand = {
    "command_name": "type-hint",
    "short_name": "t",
    "help": "✐ <t> Type hint a file or project directory.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TYPE_CHECK_COMMAND: StackOpsUtilsPyprojectTypeCheckCommand = {
    "command_name": "type-check",
    "short_name": "c",
    "help": "🧪 <c> Run the lint-and-type-check suite for a repository.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TYPE_FIX_COMMAND: StackOpsUtilsPyprojectTypeFixCommand = {
    "command_name": "type-fix",
    "short_name": "f",
    "help": "🛠 <f> Create and run the type-fix workflow from ./.ai/linters issues files.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TEST_RUNTIME_COMMAND: StackOpsUtilsPyprojectTestRuntimeCommand = {
    "command_name": "test-runtime",
    "short_name": "tr",
    "help": "🧪 <R> Create and run the runtime-test workflow for Python files under the current directory.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TEST_REFERENCE_COMMAND: StackOpsUtilsPyprojectTestReferenceCommand = {
    "command_name": "test-reference",
    "short_name": "r",
    "help": "🔎 <r> Validate _PATH_REFERENCE targets in a repository.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_SUBCOMMANDS: StackOpsUtilsPyprojectSubcommands = {
    "init-project": STACKOPS_UTILS_PYPROJECT_INIT_PROJECT_COMMAND,
    "upgrade-packages": STACKOPS_UTILS_PYPROJECT_UPGRADE_PACKAGES_COMMAND,
    "type-hint": STACKOPS_UTILS_PYPROJECT_TYPE_HINT_COMMAND,
    "type-check": STACKOPS_UTILS_PYPROJECT_TYPE_CHECK_COMMAND,
    "type-fix": STACKOPS_UTILS_PYPROJECT_TYPE_FIX_COMMAND,
    "test-runtime": STACKOPS_UTILS_PYPROJECT_TEST_RUNTIME_COMMAND,
    "test-reference": STACKOPS_UTILS_PYPROJECT_TEST_REFERENCE_COMMAND,
}

STACKOPS_UTILS_PYPROJECT_COMMAND: StackOpsUtilsPyprojectCommand = {
    "command_name": "pyproject",
    "short_name": "p",
    "help": "🐍 <p> Pyproject bootstrap and typing utilities",
    "subcommands": STACKOPS_UTILS_PYPROJECT_SUBCOMMANDS,
}

STACKOPS_UTILS_FILE_EDIT_COMMAND: StackOpsUtilsFileEditCommand = {
    "command_name": "edit",
    "short_name": "e",
    "help": "✏ <e> Open a file in the default editor.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_DOWNLOAD_COMMAND: StackOpsUtilsFileDownloadCommand = {
    "command_name": "download",
    "short_name": "d",
    "help": "↓ <d> Download a file from a URL and optionally decompress it.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_PDF_MERGE_COMMAND: StackOpsUtilsFilePDFMergeCommand = {
    "command_name": "pdf-merge",
    "short_name": "p",
    "help": "◫ <p> Merge PDF files into one.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_PDF_COMPRESS_COMMAND: StackOpsUtilsFilePDFCompressCommand = {
    "command_name": "pdf-compress",
    "short_name": "c",
    "help": "↧ <c> Compress a PDF file.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_READ_DB_COMMAND: StackOpsUtilsFileReadDBCommand = {
    "command_name": "read-db",
    "short_name": "r",
    "help": "🗃 <r> TUI DB Visualizer.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_SUBCOMMANDS: StackOpsUtilsFileSubcommands = {
    "edit": STACKOPS_UTILS_FILE_EDIT_COMMAND,
    "download": STACKOPS_UTILS_FILE_DOWNLOAD_COMMAND,
    "pdf-merge": STACKOPS_UTILS_FILE_PDF_MERGE_COMMAND,
    "pdf-compress": STACKOPS_UTILS_FILE_PDF_COMPRESS_COMMAND,
    "read-db": STACKOPS_UTILS_FILE_READ_DB_COMMAND,
}

STACKOPS_UTILS_FILE_COMMAND: StackOpsUtilsFileCommand = {
    "command_name": "file",
    "short_name": "f",
    "help": "📁 <f> File, document, and database utilities",
    "subcommands": STACKOPS_UTILS_FILE_SUBCOMMANDS,
}

STACKOPS_UTILS_SUBCOMMANDS: StackOpsUtilsSubcommands = {
    "machine": STACKOPS_UTILS_MACHINE_COMMAND,
    "pyproject": STACKOPS_UTILS_PYPROJECT_COMMAND,
    "file": STACKOPS_UTILS_FILE_COMMAND,
}

STACKOPS_UTILS_COMMAND: StackOpsUtilsCommand = {
    "command_name": "utils",
    "short_name": "u",
    "help": "<u> Utility commands",
    "subcommands": STACKOPS_UTILS_SUBCOMMANDS,
}

STACKOPS_SEEK_SEEK_COMMAND: StackOpsSeekSeekCommand = {
    "command_name": "seek",
    "short_name": None,
    "help": "stackops search helper",
    "subcommands": {},
}

STACKOPS_SEEK_SUBCOMMANDS: StackOpsSeekSubcommands = {"seek": STACKOPS_SEEK_SEEK_COMMAND}

STACKOPS_SEEK_COMMAND: StackOpsSeekCommand = {
    "command_name": "seek",
    "short_name": "s",
    "help": "<s> Search across files, text matches, and code symbols",
    "subcommands": STACKOPS_SEEK_SUBCOMMANDS,
}

STACKOPS_FIRE_COMMAND: StackOpsFireCommand = {"command_name": "fire", "short_name": "f", "help": "<f> Fire and manage jobs", "subcommands": {}}

STACKOPS_CROSHELL_COMMAND: StackOpsCroshellCommand = {
    "command_name": "croshell",
    "short_name": "r",
    "help": "<r> Cross-shell command execution",
    "subcommands": {},
}

STACKOPS_SUBCOMMANDS: StackOpsSubcommands = {
    "devops": STACKOPS_DEVOPS_COMMAND,
    "cloud": STACKOPS_CLOUD_COMMAND,
    "terminal": STACKOPS_TERMINAL_COMMAND,
    "agents": STACKOPS_AGENTS_COMMAND,
    "utils": STACKOPS_UTILS_COMMAND,
    "seek": STACKOPS_SEEK_COMMAND,
    "fire": STACKOPS_FIRE_COMMAND,
    "croshell": STACKOPS_CROSHELL_COMMAND,
}

STACKOPS_COMMAND: StackOpsCommandHierarchy = {
    "command_name": "stackops",
    "short_name": None,
    "help": "StackOps CLI - Manage your machine configurations and workflows",
    "subcommands": STACKOPS_SUBCOMMANDS,
}

STACKOPS_CLI_HIERARCHY: StackOpsCommandHierarchy = STACKOPS_COMMAND

q = STACKOPS_CLI_HIERARCHY["subcommands"]["cloud"]["subcommands"]["copy"]["help"]
