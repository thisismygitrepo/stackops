from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from stackops.utils.cli_utils.hierarchy_types import (
        StackOpsDevopsInstallCommand,
        StackOpsDevopsReposSyncCommand,
        StackOpsDevopsReposRegisterCommand,
        StackOpsDevopsReposActionCommand,
        StackOpsDevopsReposAnalyzeCommand,
        StackOpsDevopsReposGuardCommand,
        StackOpsDevopsReposVizCommand,
        StackOpsDevopsReposCountLinesCommand,
        StackOpsDevopsReposConfigLintersCommand,
        StackOpsDevopsReposCleanupCommand,
        StackOpsDevopsReposSubcommands,
        StackOpsDevopsReposCommand,
        StackOpsDevopsConfigSyncCommand,
        StackOpsDevopsConfigRegisterCommand,
        StackOpsDevopsConfigEditCommand,
        StackOpsDevopsConfigExportDotfilesCommand,
        StackOpsDevopsConfigImportDotfilesCommand,
        StackOpsDevopsConfigTerminalConfigShellCommand,
        StackOpsDevopsConfigTerminalStarshipThemeCommand,
        StackOpsDevopsConfigTerminalPwshThemeCommand,
        StackOpsDevopsConfigTerminalWeztermThemeCommand,
        StackOpsDevopsConfigTerminalGhosttyThemeCommand,
        StackOpsDevopsConfigTerminalWindowsTerminalThemeCommand,
        StackOpsDevopsConfigTerminalSubcommands,
        StackOpsDevopsConfigTerminalCommand,
        StackOpsDevopsConfigInteractiveCommand,
        StackOpsDevopsConfigCopyAssetsCommand,
        StackOpsDevopsConfigDumpCommand,
        StackOpsDevopsConfigSubcommands,
        StackOpsDevopsConfigCommand,
        StackOpsDevopsDataSyncCommand,
        StackOpsDevopsDataRegisterCommand,
        StackOpsDevopsDataEditCommand,
        StackOpsDevopsDataSubcommands,
        StackOpsDevopsDataCommand,
        StackOpsDevopsSelfInstallCommand,
        StackOpsDevopsSelfUpdateCommand,
        StackOpsDevopsSelfStatusCommand,
        StackOpsDevopsSelfSecurityScanCommand,
        StackOpsDevopsSelfSecurityListCommand,
        StackOpsDevopsSelfSecurityUploadCommand,
        StackOpsDevopsSelfSecurityDownloadCommand,
        StackOpsDevopsSelfSecurityInstallCommand,
        StackOpsDevopsSelfSecurityReportCommand,
        StackOpsDevopsSelfSecuritySubcommands,
        StackOpsDevopsSelfSecurityCommand,
        StackOpsDevopsSelfExploreSearchCommand,
        StackOpsDevopsSelfExploreTreeCommand,
        StackOpsDevopsSelfExploreDotCommand,
        StackOpsDevopsSelfExploreViewCommand,
        StackOpsDevopsSelfExploreTuiCommand,
        StackOpsDevopsSelfExploreSubcommands,
        StackOpsDevopsSelfExploreCommand,
        StackOpsDevopsSelfReadmeCommand,
        StackOpsDevopsSelfDocsCommand,
        StackOpsDevopsSelfBuildInstallerCommand,
        StackOpsDevopsSelfDownloadInstallerCommand,
        StackOpsDevopsSelfBuildDockerCommand,
        StackOpsDevopsSelfBuildGraphCommand,
        StackOpsDevopsSelfBuildAssetsUpdateCLIGraphCommand,
        StackOpsDevopsSelfBuildAssetsRegenerateChartsCommand,
        StackOpsDevopsSelfBuildAssetsSubcommands,
        StackOpsDevopsSelfBuildAssetsCommand,
        StackOpsDevopsSelfSubcommands,
        StackOpsDevopsSelfCommand,
        StackOpsDevopsNetworkShareTerminalCommand,
        StackOpsDevopsNetworkShareServerCommand,
        StackOpsDevopsNetworkSendCommand,
        StackOpsDevopsNetworkReceiveCommand,
        StackOpsDevopsNetworkShareTempFileCommand,
        StackOpsDevopsNetworkSSHInstallServerCommand,
        StackOpsDevopsNetworkSSHChangePortCommand,
        StackOpsDevopsNetworkSSHAddKeyCommand,
        StackOpsDevopsNetworkSSHDebugCommand,
        StackOpsDevopsNetworkSSHSubcommands,
        StackOpsDevopsNetworkSSHCommand,
        StackOpsDevopsNetworkDeviceSwitchPublicIpCommand,
        StackOpsDevopsNetworkDeviceWifiSelectCommand,
        StackOpsDevopsNetworkDeviceBindWSLPortCommand,
        StackOpsDevopsNetworkDeviceOpenWSLPortCommand,
        StackOpsDevopsNetworkDeviceLinkWSLWindowsCommand,
        StackOpsDevopsNetworkDeviceResetCloudflareTunnelCommand,
        StackOpsDevopsNetworkDeviceAddIpExclusionToWarpCommand,
        StackOpsDevopsNetworkDeviceSubcommands,
        StackOpsDevopsNetworkDeviceCommand,
        StackOpsDevopsNetworkShowAddressCommand,
        StackOpsDevopsNetworkVscodeShareCommand,
        StackOpsDevopsNetworkSubcommands,
        StackOpsDevopsNetworkCommand,
        StackOpsDevopsExecuteCommand,
        StackOpsDevopsSubcommands,
        StackOpsDevopsCommand,
        StackOpsCloudSyncCommand,
        StackOpsCloudCopyCommand,
        StackOpsCloudMountCommand,
        StackOpsCloudFtpxCommand,
        StackOpsCloudSubcommands,
        StackOpsCloudCommand,
        StackOpsTerminalRunCommand,
        StackOpsTerminalRunAllCommand,
        StackOpsTerminalAttachCommand,
        StackOpsTerminalKillCommand,
        StackOpsTerminalTraceCommand,
        StackOpsTerminalCreateFromFunctionCommand,
        StackOpsTerminalBalanceLoadCommand,
        StackOpsTerminalCreateTemplateCommand,
        StackOpsTerminalSummarizeCommand,
        StackOpsTerminalSubcommands,
        StackOpsTerminalCommand,
        StackOpsAgentsParallelCreateCommand,
        StackOpsAgentsParallelCreateContextCommand,
        StackOpsAgentsParallelRunParallelCommand,
        StackOpsAgentsParallelCollectCommand,
        StackOpsAgentsParallelMakeTemplateCommand,
        StackOpsAgentsParallelSubcommands,
        StackOpsAgentsParallelCommand,
        StackOpsAgentsBrowserInstallTechCommand,
        StackOpsAgentsBrowserLaunchBrowserCommand,
        StackOpsAgentsBrowserSubcommands,
        StackOpsAgentsBrowserCommand,
        StackOpsAgentsAddMcpCommand,
        StackOpsAgentsAddSkillCommand,
        StackOpsAgentsAddTodoCommand,
        StackOpsAgentsAddSymlinksCommand,
        StackOpsAgentsAddConfigCommand,
        StackOpsAgentsRunPromptCommand,
        StackOpsAgentsAskCommand,
        StackOpsAgentsSubcommands,
        StackOpsAgentsCommand,
        StackOpsUtilsMachineKillProcessCommand,
        StackOpsUtilsMachineEnvironmentCommand,
        StackOpsUtilsMachineGetMachineSpecsCommand,
        StackOpsUtilsMachineListDevicesCommand,
        StackOpsUtilsMachineMountCommand,
        StackOpsUtilsMachineSubcommands,
        StackOpsUtilsMachineCommand,
        StackOpsUtilsPyprojectInitProjectCommand,
        StackOpsUtilsPyprojectUpgradePackagesCommand,
        StackOpsUtilsPyprojectTypeHintCommand,
        StackOpsUtilsPyprojectTypeCheckCommand,
        StackOpsUtilsPyprojectTypeFixCommand,
        StackOpsUtilsPyprojectTestRuntimeCommand,
        StackOpsUtilsPyprojectTestReferenceCommand,
        StackOpsUtilsPyprojectSubcommands,
        StackOpsUtilsPyprojectCommand,
        StackOpsUtilsFileEditCommand,
        StackOpsUtilsFileDownloadCommand,
        StackOpsUtilsFilePDFMergeCommand,
        StackOpsUtilsFilePDFCompressCommand,
        StackOpsUtilsFileReadDBCommand,
        StackOpsUtilsFileSubcommands,
        StackOpsUtilsFileCommand,
        StackOpsUtilsSubcommands,
        StackOpsUtilsCommand,
        StackOpsSeekSeekCommand,
        StackOpsSeekSubcommands,
        StackOpsSeekCommand,
        StackOpsFireCommand,
        StackOpsPreviewCommand,
        StackOpsSubcommands,
        StackOpsCommandHierarchy,
    )


STACKOPS_DEVOPS_INSTALL_COMMAND: "StackOpsDevopsInstallCommand" = {
    "command_name": "install",
    "short_name": "i",
    "help": "🔧 <i> Install essential packages",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_SYNC_COMMAND: "StackOpsDevopsReposSyncCommand" = {
    "command_name": "sync",
    "short_name": "s",
    "help": "📥 <s> Clone repositories described by a repos.json specification",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_REGISTER_COMMAND: "StackOpsDevopsReposRegisterCommand" = {
    "command_name": "register",
    "short_name": "r",
    "help": "📝 <r> Record repositories into a repos.json specification",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_ACTION_COMMAND: "StackOpsDevopsReposActionCommand" = {
    "command_name": "action",
    "short_name": "a",
    "help": "🔄 <a> Run pull/commit/push actions across repositories",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_ANALYZE_COMMAND: "StackOpsDevopsReposAnalyzeCommand" = {
    "command_name": "analyze",
    "short_name": "z",
    "help": "📊 <z> Analyze repository development over time",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_GUARD_COMMAND: "StackOpsDevopsReposGuardCommand" = {
    "command_name": "guard",
    "short_name": "g",
    "help": "🔐 <g> Securely sync git repository to/from cloud with encryption",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_VIZ_COMMAND: "StackOpsDevopsReposVizCommand" = {
    "command_name": "viz",
    "short_name": "v",
    "help": "🎬 <v> Visualize repository activity using Gource",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_COUNT_LINES_COMMAND: "StackOpsDevopsReposCountLinesCommand" = {
    "command_name": "count-lines",
    "short_name": "c",
    "help": "📄 <c> Count python lines of code in current repo + historical edits.",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_CONFIG_LINTERS_COMMAND: "StackOpsDevopsReposConfigLintersCommand" = {
    "command_name": "config-linters",
    "short_name": "l",
    "help": "🧰 <l> Add linter config files to a git repository",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_CLEANUP_COMMAND: "StackOpsDevopsReposCleanupCommand" = {
    "command_name": "cleanup",
    "short_name": "n",
    "help": "🧹 <n> Clean repository directories from cache files",
    "subcommands": {},
}

STACKOPS_DEVOPS_REPOS_SUBCOMMANDS: "StackOpsDevopsReposSubcommands" = {
    "sync": STACKOPS_DEVOPS_REPOS_SYNC_COMMAND,
    "register": STACKOPS_DEVOPS_REPOS_REGISTER_COMMAND,
    "action": STACKOPS_DEVOPS_REPOS_ACTION_COMMAND,
    "analyze": STACKOPS_DEVOPS_REPOS_ANALYZE_COMMAND,
    "guard": STACKOPS_DEVOPS_REPOS_GUARD_COMMAND,
    "viz": STACKOPS_DEVOPS_REPOS_VIZ_COMMAND,
    "count-lines": STACKOPS_DEVOPS_REPOS_COUNT_LINES_COMMAND,
    "config-linters": STACKOPS_DEVOPS_REPOS_CONFIG_LINTERS_COMMAND,
    "cleanup": STACKOPS_DEVOPS_REPOS_CLEANUP_COMMAND,
}

STACKOPS_DEVOPS_REPOS_COMMAND: "StackOpsDevopsReposCommand" = {
    "command_name": "repos",
    "short_name": "r",
    "help": "📁 <r> Manage development repositories",
    "subcommands": STACKOPS_DEVOPS_REPOS_SUBCOMMANDS,
}

STACKOPS_DEVOPS_CONFIG_SYNC_COMMAND: "StackOpsDevopsConfigSyncCommand" = {
    "command_name": "sync",
    "short_name": "s",
    "help": "🔄 <s> Sync dotfiles.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_REGISTER_COMMAND: "StackOpsDevopsConfigRegisterCommand" = {
    "command_name": "register",
    "short_name": "r",
    "help": "📇 <r> Register dotfiles against user mapper.yaml",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_EDIT_COMMAND: "StackOpsDevopsConfigEditCommand" = {
    "command_name": "edit",
    "short_name": "e",
    "help": "📝 <e> Open dotfiles mapper.yaml in nano, hx, or code.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_EXPORT_DOTFILES_COMMAND: "StackOpsDevopsConfigExportDotfilesCommand" = {
    "command_name": "export-dotfiles",
    "short_name": "E",
    "help": "📤 <E> Export dotfiles for migration to new machine.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_IMPORT_DOTFILES_COMMAND: "StackOpsDevopsConfigImportDotfilesCommand" = {
    "command_name": "import-dotfiles",
    "short_name": "I",
    "help": "📥 <I> Import dotfiles from exported archive.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_CONFIG_SHELL_COMMAND: "StackOpsDevopsConfigTerminalConfigShellCommand" = {
    "command_name": "config-shell",
    "short_name": "s",
    "help": "🐚 <s> Create or configure a shell profile.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_STARSHIP_THEME_COMMAND: "StackOpsDevopsConfigTerminalStarshipThemeCommand" = {
    "command_name": "starship-theme",
    "short_name": "t",
    "help": "⭐ <t> Select starship prompt theme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_PWSH_THEME_COMMAND: "StackOpsDevopsConfigTerminalPwshThemeCommand" = {
    "command_name": "pwsh-theme",
    "short_name": "T",
    "help": "⚡ <T> Select powershell prompt theme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_WEZTERM_THEME_COMMAND: "StackOpsDevopsConfigTerminalWeztermThemeCommand" = {
    "command_name": "wezterm-theme",
    "short_name": "W",
    "help": "💻 <W> Select WezTerm terminal theme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_GHOSTTY_THEME_COMMAND: "StackOpsDevopsConfigTerminalGhosttyThemeCommand" = {
    "command_name": "ghostty-theme",
    "short_name": "g",
    "help": "👻 <g> Select Ghostty terminal theme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_WINDOWS_TERMINAL_THEME_COMMAND: "StackOpsDevopsConfigTerminalWindowsTerminalThemeCommand" = {
    "command_name": "windows-terminal-theme",
    "short_name": "x",
    "help": "🪟 <x> Select Windows Terminal color scheme.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_SUBCOMMANDS: "StackOpsDevopsConfigTerminalSubcommands" = {
    "config-shell": STACKOPS_DEVOPS_CONFIG_TERMINAL_CONFIG_SHELL_COMMAND,
    "starship-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_STARSHIP_THEME_COMMAND,
    "pwsh-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_PWSH_THEME_COMMAND,
    "wezterm-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_WEZTERM_THEME_COMMAND,
    "ghostty-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_GHOSTTY_THEME_COMMAND,
    "windows-terminal-theme": STACKOPS_DEVOPS_CONFIG_TERMINAL_WINDOWS_TERMINAL_THEME_COMMAND,
}

STACKOPS_DEVOPS_CONFIG_TERMINAL_COMMAND: "StackOpsDevopsConfigTerminalCommand" = {
    "command_name": "terminal",
    "short_name": "t",
    "help": "🐚 <t> Configure your terminal profile.",
    "subcommands": STACKOPS_DEVOPS_CONFIG_TERMINAL_SUBCOMMANDS,
}

STACKOPS_DEVOPS_CONFIG_INTERACTIVE_COMMAND: "StackOpsDevopsConfigInteractiveCommand" = {
    "command_name": "interactive",
    "short_name": "i",
    "help": "🤖 <i> Interactive configuration of machine.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_COPY_ASSETS_COMMAND: "StackOpsDevopsConfigCopyAssetsCommand" = {
    "command_name": "copy-assets",
    "short_name": "c",
    "help": "📋 <c> Copy asset files from library to machine.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_DUMP_COMMAND: "StackOpsDevopsConfigDumpCommand" = {
    "command_name": "dump",
    "short_name": "d",
    "help": "📦 <d> Dump example configuration files and init scripts.",
    "subcommands": {},
}

STACKOPS_DEVOPS_CONFIG_SUBCOMMANDS: "StackOpsDevopsConfigSubcommands" = {
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

STACKOPS_DEVOPS_CONFIG_COMMAND: "StackOpsDevopsConfigCommand" = {
    "command_name": "config",
    "short_name": "c",
    "help": "🔩 <c> Configuration management",
    "subcommands": STACKOPS_DEVOPS_CONFIG_SUBCOMMANDS,
}

STACKOPS_DEVOPS_DATA_SYNC_COMMAND: "StackOpsDevopsDataSyncCommand" = {
    "command_name": "sync",
    "short_name": "s",
    "help": "🔄 <s> Back up or retrieve files and directories using rclone or share links.",
    "subcommands": {},
}

STACKOPS_DEVOPS_DATA_REGISTER_COMMAND: "StackOpsDevopsDataRegisterCommand" = {
    "command_name": "register",
    "short_name": "r",
    "help": "📝 <r> Register a new backup entry in user mapper/data.yaml.",
    "subcommands": {},
}

STACKOPS_DEVOPS_DATA_EDIT_COMMAND: "StackOpsDevopsDataEditCommand" = {
    "command_name": "edit",
    "short_name": "e",
    "help": "✏️ <e> Open backup configuration file in nano, hx, or code.",
    "subcommands": {},
}

STACKOPS_DEVOPS_DATA_SUBCOMMANDS: "StackOpsDevopsDataSubcommands" = {
    "sync": STACKOPS_DEVOPS_DATA_SYNC_COMMAND,
    "register": STACKOPS_DEVOPS_DATA_REGISTER_COMMAND,
    "edit": STACKOPS_DEVOPS_DATA_EDIT_COMMAND,
}

STACKOPS_DEVOPS_DATA_COMMAND: "StackOpsDevopsDataCommand" = {
    "command_name": "data",
    "short_name": "d",
    "help": "💾 <d> Data management",
    "subcommands": STACKOPS_DEVOPS_DATA_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_INSTALL_COMMAND: "StackOpsDevopsSelfInstallCommand" = {
    "command_name": "install",
    "short_name": "i",
    "help": "📋 <i> install stackops locally for nightly updates.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_UPDATE_COMMAND: "StackOpsDevopsSelfUpdateCommand" = {
    "command_name": "update",
    "short_name": "u",
    "help": "🔄 <u> UPDATE stackops",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_STATUS_COMMAND: "StackOpsDevopsSelfStatusCommand" = {
    "command_name": "status",
    "short_name": "s",
    "help": "📊 <s> STATUS of machine, shell profile, apps, symlinks, dotfiles, etc.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_SCAN_COMMAND: "StackOpsDevopsSelfSecurityScanCommand" = {
    "command_name": "scan",
    "short_name": "s",
    "help": "<s> Scan installed apps or a single file path with VirusTotal",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_LIST_COMMAND: "StackOpsDevopsSelfSecurityListCommand" = {
    "command_name": "list",
    "short_name": "l",
    "help": "<l> List installed apps, optionally filtered by comma-separated app names",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_UPLOAD_COMMAND: "StackOpsDevopsSelfSecurityUploadCommand" = {
    "command_name": "upload",
    "short_name": "u",
    "help": "<u> Upload a local file to cloud storage",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_DOWNLOAD_COMMAND: "StackOpsDevopsSelfSecurityDownloadCommand" = {
    "command_name": "download",
    "short_name": "d",
    "help": "<d> Download a file from Google Drive",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_INSTALL_COMMAND: "StackOpsDevopsSelfSecurityInstallCommand" = {
    "command_name": "install",
    "short_name": "i",
    "help": "<i> Install safe apps from app metadata report",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_REPORT_COMMAND: "StackOpsDevopsSelfSecurityReportCommand" = {
    "command_name": "report",
    "short_name": "r",
    "help": "<r> Show the full saved scan report by default, or CSV rows/summary stats",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_SECURITY_SUBCOMMANDS: "StackOpsDevopsSelfSecuritySubcommands" = {
    "scan": STACKOPS_DEVOPS_SELF_SECURITY_SCAN_COMMAND,
    "list": STACKOPS_DEVOPS_SELF_SECURITY_LIST_COMMAND,
    "upload": STACKOPS_DEVOPS_SELF_SECURITY_UPLOAD_COMMAND,
    "download": STACKOPS_DEVOPS_SELF_SECURITY_DOWNLOAD_COMMAND,
    "install": STACKOPS_DEVOPS_SELF_SECURITY_INSTALL_COMMAND,
    "report": STACKOPS_DEVOPS_SELF_SECURITY_REPORT_COMMAND,
}

STACKOPS_DEVOPS_SELF_SECURITY_COMMAND: "StackOpsDevopsSelfSecurityCommand" = {
    "command_name": "security",
    "short_name": "y",
    "help": "🔐 <y> Security related CLI tools.",
    "subcommands": STACKOPS_DEVOPS_SELF_SECURITY_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_EXPLORE_SEARCH_COMMAND: "StackOpsDevopsSelfExploreSearchCommand" = {
    "command_name": "search",
    "short_name": "s",
    "help": "🔎 <s> Search CLI graph entries and show the selected command summary.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_TREE_COMMAND: "StackOpsDevopsSelfExploreTreeCommand" = {
    "command_name": "tree",
    "short_name": "t",
    "help": "🌳 <t> Render a rich tree view in the terminal.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_DOT_COMMAND: "StackOpsDevopsSelfExploreDotCommand" = {
    "command_name": "dot",
    "short_name": "d",
    "help": "🧩 <d> Export the graph as Graphviz DOT.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_VIEW_COMMAND: "StackOpsDevopsSelfExploreViewCommand" = {
    "command_name": "view",
    "short_name": "v",
    "help": "📊 <v> Render a Plotly hierarchy chart.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_TUI_COMMAND: "StackOpsDevopsSelfExploreTuiCommand" = {
    "command_name": "tui",
    "short_name": "u",
    "help": "📚 <u> NAVIGATE command structure with TUI",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_EXPLORE_SUBCOMMANDS: "StackOpsDevopsSelfExploreSubcommands" = {
    "search": STACKOPS_DEVOPS_SELF_EXPLORE_SEARCH_COMMAND,
    "tree": STACKOPS_DEVOPS_SELF_EXPLORE_TREE_COMMAND,
    "dot": STACKOPS_DEVOPS_SELF_EXPLORE_DOT_COMMAND,
    "view": STACKOPS_DEVOPS_SELF_EXPLORE_VIEW_COMMAND,
    "tui": STACKOPS_DEVOPS_SELF_EXPLORE_TUI_COMMAND,
}

STACKOPS_DEVOPS_SELF_EXPLORE_COMMAND: "StackOpsDevopsSelfExploreCommand" = {
    "command_name": "explore",
    "short_name": "x",
    "help": "🧭 <x> Explore the StackOps CLI graph.",
    "subcommands": STACKOPS_DEVOPS_SELF_EXPLORE_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_README_COMMAND: "StackOpsDevopsSelfReadmeCommand" = {
    "command_name": "readme",
    "short_name": "r",
    "help": "📚 <r> render readme markdown in terminal.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_DOCS_COMMAND: "StackOpsDevopsSelfDocsCommand" = {
    "command_name": "docs",
    "short_name": "o",
    "help": "📚 <o> Serve local docs with preview URLs.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_INSTALLER_COMMAND: "StackOpsDevopsSelfBuildInstallerCommand" = {
    "command_name": "build-installer",
    "short_name": "e",
    "help": "📤 <e> Build an offline installer.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_DOWNLOAD_INSTALLER_COMMAND: "StackOpsDevopsSelfDownloadInstallerCommand" = {
    "command_name": "download-installer",
    "short_name": "D",
    "help": "📥 <D> Download an offline installer.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_DOCKER_COMMAND: "StackOpsDevopsSelfBuildDockerCommand" = {
    "command_name": "build-docker",
    "short_name": "d",
    "help": "🧱 <d> Build docker images (wraps jobs/shell/docker_build_and_publish.sh)",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_GRAPH_COMMAND: "StackOpsDevopsSelfBuildGraphCommand" = {
    "command_name": "build-graph",
    "short_name": "g",
    "help": "🕸 <g> Build the architecture dependency graph.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_ASSETS_UPDATE_CLI_GRAPH_COMMAND: "StackOpsDevopsSelfBuildAssetsUpdateCLIGraphCommand" = {
    "command_name": "update-cli-graph",
    "short_name": "g",
    "help": "🧩 <g> Regenerate the checked-in CLI graph snapshot.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_ASSETS_REGENERATE_CHARTS_COMMAND: "StackOpsDevopsSelfBuildAssetsRegenerateChartsCommand" = {
    "command_name": "regenerate-charts",
    "short_name": "c",
    "help": "☀ <c> Regenerate the checked-in sunburst HTML chart.",
    "subcommands": {},
}

STACKOPS_DEVOPS_SELF_BUILD_ASSETS_SUBCOMMANDS: "StackOpsDevopsSelfBuildAssetsSubcommands" = {
    "update-cli-graph": STACKOPS_DEVOPS_SELF_BUILD_ASSETS_UPDATE_CLI_GRAPH_COMMAND,
    "regenerate-charts": STACKOPS_DEVOPS_SELF_BUILD_ASSETS_REGENERATE_CHARTS_COMMAND,
}

STACKOPS_DEVOPS_SELF_BUILD_ASSETS_COMMAND: "StackOpsDevopsSelfBuildAssetsCommand" = {
    "command_name": "build-assets",
    "short_name": "a",
    "help": "🗂 <a> Regenerate repo-local CLI graph assets.",
    "subcommands": STACKOPS_DEVOPS_SELF_BUILD_ASSETS_SUBCOMMANDS,
}

STACKOPS_DEVOPS_SELF_SUBCOMMANDS: "StackOpsDevopsSelfSubcommands" = {
    "install": STACKOPS_DEVOPS_SELF_INSTALL_COMMAND,
    "update": STACKOPS_DEVOPS_SELF_UPDATE_COMMAND,
    "status": STACKOPS_DEVOPS_SELF_STATUS_COMMAND,
    "security": STACKOPS_DEVOPS_SELF_SECURITY_COMMAND,
    "explore": STACKOPS_DEVOPS_SELF_EXPLORE_COMMAND,
    "readme": STACKOPS_DEVOPS_SELF_README_COMMAND,
    "docs": STACKOPS_DEVOPS_SELF_DOCS_COMMAND,
    "build-installer": STACKOPS_DEVOPS_SELF_BUILD_INSTALLER_COMMAND,
    "download-installer": STACKOPS_DEVOPS_SELF_DOWNLOAD_INSTALLER_COMMAND,
    "build-docker": STACKOPS_DEVOPS_SELF_BUILD_DOCKER_COMMAND,
    "build-graph": STACKOPS_DEVOPS_SELF_BUILD_GRAPH_COMMAND,
    "build-assets": STACKOPS_DEVOPS_SELF_BUILD_ASSETS_COMMAND,
}

STACKOPS_DEVOPS_SELF_COMMAND: "StackOpsDevopsSelfCommand" = {
    "command_name": "self",
    "short_name": "s",
    "help": "🔧 <s> Self management",
    "subcommands": STACKOPS_DEVOPS_SELF_SUBCOMMANDS,
}

STACKOPS_DEVOPS_NETWORK_SHARE_TERMINAL_COMMAND: "StackOpsDevopsNetworkShareTerminalCommand" = {
    "command_name": "share-terminal",
    "short_name": "t",
    "help": "📡 <t> Share terminal via web browser",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SHARE_SERVER_COMMAND: "StackOpsDevopsNetworkShareServerCommand" = {
    "command_name": "share-server",
    "short_name": "s",
    "help": "🌐 <s> Start local/global server to share files/folders via web browser",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SEND_COMMAND: "StackOpsDevopsNetworkSendCommand" = {
    "command_name": "send",
    "short_name": "f",
    "help": "📁 <f> send files from here.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_RECEIVE_COMMAND: "StackOpsDevopsNetworkReceiveCommand" = {
    "command_name": "receive",
    "short_name": "r",
    "help": "📁 <r> receive files to here.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SHARE_TEMP_FILE_COMMAND: "StackOpsDevopsNetworkShareTempFileCommand" = {
    "command_name": "share-temp-file",
    "short_name": "T",
    "help": "🌡 <T> Share a file via temp.sh",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_INSTALL_SERVER_COMMAND: "StackOpsDevopsNetworkSSHInstallServerCommand" = {
    "command_name": "install-server",
    "short_name": "i",
    "help": "📡 <i> Install SSH server",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_CHANGE_PORT_COMMAND: "StackOpsDevopsNetworkSSHChangePortCommand" = {
    "command_name": "change-port",
    "short_name": "p",
    "help": "🔌 <p> Change SSH port (Linux/WSL only)",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_ADD_KEY_COMMAND: "StackOpsDevopsNetworkSSHAddKeyCommand" = {
    "command_name": "add-key",
    "short_name": "k",
    "help": "🔑 <k> Add SSH public key to this machine",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_DEBUG_COMMAND: "StackOpsDevopsNetworkSSHDebugCommand" = {
    "command_name": "debug",
    "short_name": "d",
    "help": "🐛 <d> Debug SSH connection",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SSH_SUBCOMMANDS: "StackOpsDevopsNetworkSSHSubcommands" = {
    "install-server": STACKOPS_DEVOPS_NETWORK_SSH_INSTALL_SERVER_COMMAND,
    "change-port": STACKOPS_DEVOPS_NETWORK_SSH_CHANGE_PORT_COMMAND,
    "add-key": STACKOPS_DEVOPS_NETWORK_SSH_ADD_KEY_COMMAND,
    "debug": STACKOPS_DEVOPS_NETWORK_SSH_DEBUG_COMMAND,
}

STACKOPS_DEVOPS_NETWORK_SSH_COMMAND: "StackOpsDevopsNetworkSSHCommand" = {
    "command_name": "ssh",
    "short_name": "S",
    "help": "🔐 <S> SSH subcommands",
    "subcommands": STACKOPS_DEVOPS_NETWORK_SSH_SUBCOMMANDS,
}

STACKOPS_DEVOPS_NETWORK_DEVICE_SWITCH_PUBLIC_IP_COMMAND: "StackOpsDevopsNetworkDeviceSwitchPublicIpCommand" = {
    "command_name": "switch-public-ip",
    "short_name": "s",
    "help": "🔁 <s> Switch public IP address (Cloudflare WARP)",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_WIFI_SELECT_COMMAND: "StackOpsDevopsNetworkDeviceWifiSelectCommand" = {
    "command_name": "wifi-select",
    "short_name": "w",
    "help": "📶 <w> WiFi connection utility.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_BIND_WSL_PORT_COMMAND: "StackOpsDevopsNetworkDeviceBindWSLPortCommand" = {
    "command_name": "bind-wsl-port",
    "short_name": "b",
    "help": "🔌 <b> Bind WSL port to Windows host",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_OPEN_WSL_PORT_COMMAND: "StackOpsDevopsNetworkDeviceOpenWSLPortCommand" = {
    "command_name": "open-wsl-port",
    "short_name": "o",
    "help": "🔥 <o> Open Windows firewall ports for WSL.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_LINK_WSL_WINDOWS_COMMAND: "StackOpsDevopsNetworkDeviceLinkWSLWindowsCommand" = {
    "command_name": "link-wsl-windows",
    "short_name": "l",
    "help": "🔗 <l> Link WSL home and Windows home directories.",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_RESET_CLOUDFLARE_TUNNEL_COMMAND: "StackOpsDevopsNetworkDeviceResetCloudflareTunnelCommand" = {
    "command_name": "reset-cloudflare-tunnel",
    "short_name": "r",
    "help": "☁ <r> Reset Cloudflare tunnel service",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_ADD_IP_EXCLUSION_TO_WARP_COMMAND: "StackOpsDevopsNetworkDeviceAddIpExclusionToWarpCommand" = {
    "command_name": "add-ip-exclusion-to-warp",
    "short_name": "p",
    "help": "🚫 <p> Add IP exclusion to WARP",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_DEVICE_SUBCOMMANDS: "StackOpsDevopsNetworkDeviceSubcommands" = {
    "switch-public-ip": STACKOPS_DEVOPS_NETWORK_DEVICE_SWITCH_PUBLIC_IP_COMMAND,
    "wifi-select": STACKOPS_DEVOPS_NETWORK_DEVICE_WIFI_SELECT_COMMAND,
    "bind-wsl-port": STACKOPS_DEVOPS_NETWORK_DEVICE_BIND_WSL_PORT_COMMAND,
    "open-wsl-port": STACKOPS_DEVOPS_NETWORK_DEVICE_OPEN_WSL_PORT_COMMAND,
    "link-wsl-windows": STACKOPS_DEVOPS_NETWORK_DEVICE_LINK_WSL_WINDOWS_COMMAND,
    "reset-cloudflare-tunnel": STACKOPS_DEVOPS_NETWORK_DEVICE_RESET_CLOUDFLARE_TUNNEL_COMMAND,
    "add-ip-exclusion-to-warp": STACKOPS_DEVOPS_NETWORK_DEVICE_ADD_IP_EXCLUSION_TO_WARP_COMMAND,
}

STACKOPS_DEVOPS_NETWORK_DEVICE_COMMAND: "StackOpsDevopsNetworkDeviceCommand" = {
    "command_name": "device",
    "short_name": "d",
    "help": "🖥 <d> Device subcommands",
    "subcommands": STACKOPS_DEVOPS_NETWORK_DEVICE_SUBCOMMANDS,
}

STACKOPS_DEVOPS_NETWORK_SHOW_ADDRESS_COMMAND: "StackOpsDevopsNetworkShowAddressCommand" = {
    "command_name": "show-address",
    "short_name": "a",
    "help": "📌 <a> Show this computer addresses on network",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_VSCODE_SHARE_COMMAND: "StackOpsDevopsNetworkVscodeShareCommand" = {
    "command_name": "vscode-share",
    "short_name": "v",
    "help": "💻 <v> Share workspace via VS Code Tunnels",
    "subcommands": {},
}

STACKOPS_DEVOPS_NETWORK_SUBCOMMANDS: "StackOpsDevopsNetworkSubcommands" = {
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

STACKOPS_DEVOPS_NETWORK_COMMAND: "StackOpsDevopsNetworkCommand" = {
    "command_name": "network",
    "short_name": "n",
    "help": "🌐 <n> Network management",
    "subcommands": STACKOPS_DEVOPS_NETWORK_SUBCOMMANDS,
}

STACKOPS_DEVOPS_EXECUTE_COMMAND: "StackOpsDevopsExecuteCommand" = {
    "command_name": "execute",
    "short_name": "e",
    "help": "🚀 <e> Execute python/shell scripts from pre-defined directories or as command",
    "subcommands": {},
}

STACKOPS_DEVOPS_SUBCOMMANDS: "StackOpsDevopsSubcommands" = {
    "install": STACKOPS_DEVOPS_INSTALL_COMMAND,
    "repos": STACKOPS_DEVOPS_REPOS_COMMAND,
    "config": STACKOPS_DEVOPS_CONFIG_COMMAND,
    "data": STACKOPS_DEVOPS_DATA_COMMAND,
    "self": STACKOPS_DEVOPS_SELF_COMMAND,
    "network": STACKOPS_DEVOPS_NETWORK_COMMAND,
    "execute": STACKOPS_DEVOPS_EXECUTE_COMMAND,
}

STACKOPS_DEVOPS_COMMAND: "StackOpsDevopsCommand" = {
    "command_name": "devops",
    "short_name": "d",
    "help": "<d> DevOps related commands",
    "subcommands": STACKOPS_DEVOPS_SUBCOMMANDS,
}

STACKOPS_CLOUD_SYNC_COMMAND: "StackOpsCloudSyncCommand" = {
    "command_name": "sync",
    "short_name": "s",
    "help": "🔄 <s> Synchronize files/folders between local and cloud storage.",
    "subcommands": {},
}

STACKOPS_CLOUD_COPY_COMMAND: "StackOpsCloudCopyCommand" = {
    "command_name": "copy",
    "short_name": "c",
    "help": "📤 <c> Upload or 📥 Download files/folders to/from cloud storage.",
    "subcommands": {},
}

STACKOPS_CLOUD_MOUNT_COMMAND: "StackOpsCloudMountCommand" = {
    "command_name": "mount",
    "short_name": "m",
    "help": "🔗 <m> Mount cloud storage services as local drives.",
    "subcommands": {},
}

STACKOPS_CLOUD_FTPX_COMMAND: "StackOpsCloudFtpxCommand" = {
    "command_name": "ftpx",
    "short_name": "f",
    "help": "📦 <f> File transfer utility through SSH.",
    "subcommands": {},
}

STACKOPS_CLOUD_SUBCOMMANDS: "StackOpsCloudSubcommands" = {
    "sync": STACKOPS_CLOUD_SYNC_COMMAND,
    "copy": STACKOPS_CLOUD_COPY_COMMAND,
    "mount": STACKOPS_CLOUD_MOUNT_COMMAND,
    "ftpx": STACKOPS_CLOUD_FTPX_COMMAND,
}

STACKOPS_CLOUD_COMMAND: "StackOpsCloudCommand" = {
    "command_name": "cloud",
    "short_name": "c",
    "help": "<c> Cloud management commands",
    "subcommands": STACKOPS_CLOUD_SUBCOMMANDS,
}

STACKOPS_TERMINAL_RUN_COMMAND: "StackOpsTerminalRunCommand" = {
    "command_name": "run",
    "short_name": "r",
    "help": "<r> Run the selected layout(s)",
    "subcommands": {},
}

STACKOPS_TERMINAL_RUN_ALL_COMMAND: "StackOpsTerminalRunAllCommand" = {
    "command_name": "run-all",
    "short_name": "R",
    "help": "<R> Dynamically run every layout in a file",
    "subcommands": {},
}

STACKOPS_TERMINAL_ATTACH_COMMAND: "StackOpsTerminalAttachCommand" = {
    "command_name": "attach",
    "short_name": "a",
    "help": "<a> Attach to a session target",
    "subcommands": {},
}

STACKOPS_TERMINAL_KILL_COMMAND: "StackOpsTerminalKillCommand" = {
    "command_name": "kill",
    "short_name": "k",
    "help": "<k> Kill a session target",
    "subcommands": {},
}

STACKOPS_TERMINAL_TRACE_COMMAND: "StackOpsTerminalTraceCommand" = {
    "command_name": "trace",
    "short_name": "t",
    "help": "<t> Trace a tmux session until it settles",
    "subcommands": {},
}

STACKOPS_TERMINAL_CREATE_FROM_FUNCTION_COMMAND: "StackOpsTerminalCreateFromFunctionCommand" = {
    "command_name": "create-from-function",
    "short_name": "c",
    "help": "<c> Create a layout from a function",
    "subcommands": {},
}

STACKOPS_TERMINAL_BALANCE_LOAD_COMMAND: "StackOpsTerminalBalanceLoadCommand" = {
    "command_name": "balance-load",
    "short_name": "b",
    "help": "<b> Balance the load across sessions",
    "subcommands": {},
}

STACKOPS_TERMINAL_CREATE_TEMPLATE_COMMAND: "StackOpsTerminalCreateTemplateCommand" = {
    "command_name": "create-template",
    "short_name": "p",
    "help": "<p> Create a layout template file",
    "subcommands": {},
}

STACKOPS_TERMINAL_SUMMARIZE_COMMAND: "StackOpsTerminalSummarizeCommand" = {
    "command_name": "summarize",
    "short_name": "s",
    "help": "<s> Summarize a layout file",
    "subcommands": {},
}

STACKOPS_TERMINAL_SUBCOMMANDS: "StackOpsTerminalSubcommands" = {
    "run": STACKOPS_TERMINAL_RUN_COMMAND,
    "run-all": STACKOPS_TERMINAL_RUN_ALL_COMMAND,
    "attach": STACKOPS_TERMINAL_ATTACH_COMMAND,
    "kill": STACKOPS_TERMINAL_KILL_COMMAND,
    "trace": STACKOPS_TERMINAL_TRACE_COMMAND,
    "create-from-function": STACKOPS_TERMINAL_CREATE_FROM_FUNCTION_COMMAND,
    "balance-load": STACKOPS_TERMINAL_BALANCE_LOAD_COMMAND,
    "create-template": STACKOPS_TERMINAL_CREATE_TEMPLATE_COMMAND,
    "summarize": STACKOPS_TERMINAL_SUMMARIZE_COMMAND,
}

STACKOPS_TERMINAL_COMMAND: "StackOpsTerminalCommand" = {
    "command_name": "terminal",
    "short_name": "t",
    "help": "<t> Terminal and layout management",
    "subcommands": STACKOPS_TERMINAL_SUBCOMMANDS,
}

STACKOPS_AGENTS_PARALLEL_CREATE_COMMAND: "StackOpsAgentsParallelCreateCommand" = {
    "command_name": "create",
    "short_name": "c",
    "help": "<c> Create agents layout file, ready to run.",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_CREATE_CONTEXT_COMMAND: "StackOpsAgentsParallelCreateContextCommand" = {
    "command_name": "create-context",
    "short_name": "x",
    "help": "<x> Run prompt and ask agent to persist context",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_RUN_PARALLEL_COMMAND: "StackOpsAgentsParallelRunParallelCommand" = {
    "command_name": "run-parallel",
    "short_name": "r",
    "help": "<r> Run named parallel workflow from YAML",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_COLLECT_COMMAND: "StackOpsAgentsParallelCollectCommand" = {
    "command_name": "collect",
    "short_name": "T",
    "help": "<T> Collect all agent materials into a single file.",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_MAKE_TEMPLATE_COMMAND: "StackOpsAgentsParallelMakeTemplateCommand" = {
    "command_name": "make-template",
    "short_name": "p",
    "help": "<p> Create a template for fire agents",
    "subcommands": {},
}

STACKOPS_AGENTS_PARALLEL_SUBCOMMANDS: "StackOpsAgentsParallelSubcommands" = {
    "create": STACKOPS_AGENTS_PARALLEL_CREATE_COMMAND,
    "create-context": STACKOPS_AGENTS_PARALLEL_CREATE_CONTEXT_COMMAND,
    "run-parallel": STACKOPS_AGENTS_PARALLEL_RUN_PARALLEL_COMMAND,
    "collect": STACKOPS_AGENTS_PARALLEL_COLLECT_COMMAND,
    "make-template": STACKOPS_AGENTS_PARALLEL_MAKE_TEMPLATE_COMMAND,
}

STACKOPS_AGENTS_PARALLEL_COMMAND: "StackOpsAgentsParallelCommand" = {
    "command_name": "parallel",
    "short_name": "p",
    "help": "<p> Parallel agent workflow commands",
    "subcommands": STACKOPS_AGENTS_PARALLEL_SUBCOMMANDS,
}

STACKOPS_AGENTS_BROWSER_INSTALL_TECH_COMMAND: "StackOpsAgentsBrowserInstallTechCommand" = {
    "command_name": "install-tech",
    "short_name": "i",
    "help": "<i> Install agent-browser, playwright-cli, or MCP configs",
    "subcommands": {},
}

STACKOPS_AGENTS_BROWSER_LAUNCH_BROWSER_COMMAND: "StackOpsAgentsBrowserLaunchBrowserCommand" = {
    "command_name": "launch-browser",
    "short_name": "l",
    "help": "<l> Launch Chrome or Brave with CDP profile",
    "subcommands": {},
}

STACKOPS_AGENTS_BROWSER_SUBCOMMANDS: "StackOpsAgentsBrowserSubcommands" = {
    "install-tech": STACKOPS_AGENTS_BROWSER_INSTALL_TECH_COMMAND,
    "launch-browser": STACKOPS_AGENTS_BROWSER_LAUNCH_BROWSER_COMMAND,
}

STACKOPS_AGENTS_BROWSER_COMMAND: "StackOpsAgentsBrowserCommand" = {
    "command_name": "browser",
    "short_name": "b",
    "help": "<b> Browser automation for agent CLIs/MCP",
    "subcommands": STACKOPS_AGENTS_BROWSER_SUBCOMMANDS,
}

STACKOPS_AGENTS_ADD_MCP_COMMAND: "StackOpsAgentsAddMcpCommand" = {
    "command_name": "add-mcp",
    "short_name": "m",
    "help": "<m> Resolve catalog MCP entries or supported skills",
    "subcommands": {},
}

STACKOPS_AGENTS_ADD_SKILL_COMMAND: "StackOpsAgentsAddSkillCommand" = {
    "command_name": "add-skill",
    "short_name": "s",
    "help": "<s> Add a skill to an agent",
    "subcommands": {},
}

STACKOPS_AGENTS_ADD_TODO_COMMAND: "StackOpsAgentsAddTodoCommand" = {
    "command_name": "add-todo",
    "short_name": "d",
    "help": "<d> Generate a markdown file listing all Python files in the repo",
    "subcommands": {},
}

STACKOPS_AGENTS_ADD_SYMLINKS_COMMAND: "StackOpsAgentsAddSymlinksCommand" = {
    "command_name": "add-symlinks",
    "short_name": "l",
    "help": "<l> Create symlinks to the current repo in ~/code_copies/",
    "subcommands": {},
}

STACKOPS_AGENTS_ADD_CONFIG_COMMAND: "StackOpsAgentsAddConfigCommand" = {
    "command_name": "add-config",
    "short_name": "c",
    "help": "<c> Initialize AI configurations in the current repository",
    "subcommands": {},
}

STACKOPS_AGENTS_RUN_PROMPT_COMMAND: "StackOpsAgentsRunPromptCommand" = {
    "command_name": "run-prompt",
    "short_name": "r",
    "help": "<r> Run one prompt via selected agent",
    "subcommands": {},
}

STACKOPS_AGENTS_ASK_COMMAND: "StackOpsAgentsAskCommand" = {
    "command_name": "ask",
    "short_name": "a",
    "help": "<a> Ask a selected agent directly",
    "subcommands": {},
}

STACKOPS_AGENTS_SUBCOMMANDS: "StackOpsAgentsSubcommands" = {
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

STACKOPS_AGENTS_COMMAND: "StackOpsAgentsCommand" = {
    "command_name": "agents",
    "short_name": "a",
    "help": "<a> 🤖 AI Agents management commands",
    "subcommands": STACKOPS_AGENTS_SUBCOMMANDS,
}

STACKOPS_UTILS_MACHINE_KILL_PROCESS_COMMAND: "StackOpsUtilsMachineKillProcessCommand" = {
    "command_name": "kill-process",
    "short_name": "k",
    "help": "⚔ <k> Choose a process to kill",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_ENVIRONMENT_COMMAND: "StackOpsUtilsMachineEnvironmentCommand" = {
    "command_name": "environment",
    "short_name": "v",
    "help": "⌘ <v> Navigate ENV/PATH variables. Default: fuzzy picker with preview; use --tui for Textual.",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_GET_MACHINE_SPECS_COMMAND: "StackOpsUtilsMachineGetMachineSpecsCommand" = {
    "command_name": "get-machine-specs",
    "short_name": "s",
    "help": "🖥 <s> Get machine specifications.",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_LIST_DEVICES_COMMAND: "StackOpsUtilsMachineListDevicesCommand" = {
    "command_name": "list-devices",
    "short_name": "l",
    "help": "💽 <l> List available devices for mounting.",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_MOUNT_COMMAND: "StackOpsUtilsMachineMountCommand" = {
    "command_name": "mount",
    "short_name": "m",
    "help": "🔌 <m> Mount a device to a mount point.",
    "subcommands": {},
}

STACKOPS_UTILS_MACHINE_SUBCOMMANDS: "StackOpsUtilsMachineSubcommands" = {
    "kill-process": STACKOPS_UTILS_MACHINE_KILL_PROCESS_COMMAND,
    "environment": STACKOPS_UTILS_MACHINE_ENVIRONMENT_COMMAND,
    "get-machine-specs": STACKOPS_UTILS_MACHINE_GET_MACHINE_SPECS_COMMAND,
    "list-devices": STACKOPS_UTILS_MACHINE_LIST_DEVICES_COMMAND,
    "mount": STACKOPS_UTILS_MACHINE_MOUNT_COMMAND,
}

STACKOPS_UTILS_MACHINE_COMMAND: "StackOpsUtilsMachineCommand" = {
    "command_name": "machine",
    "short_name": "m",
    "help": "🖥 <m> Machine and device utilities",
    "subcommands": STACKOPS_UTILS_MACHINE_SUBCOMMANDS,
}

STACKOPS_UTILS_PYPROJECT_INIT_PROJECT_COMMAND: "StackOpsUtilsPyprojectInitProjectCommand" = {
    "command_name": "init-project",
    "short_name": "i",
    "help": "✦ <i> Initialize a project with a uv virtual environment and install dev packages.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_UPGRADE_PACKAGES_COMMAND: "StackOpsUtilsPyprojectUpgradePackagesCommand" = {
    "command_name": "upgrade-packages",
    "short_name": "a",
    "help": "↑ <a> Upgrade project dependencies.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TYPE_HINT_COMMAND: "StackOpsUtilsPyprojectTypeHintCommand" = {
    "command_name": "type-hint",
    "short_name": "t",
    "help": "✐ <t> Type hint a file or project directory.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TYPE_CHECK_COMMAND: "StackOpsUtilsPyprojectTypeCheckCommand" = {
    "command_name": "type-check",
    "short_name": "c",
    "help": "🧪 <c> Run the lint-and-type-check suite for a repository.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TYPE_FIX_COMMAND: "StackOpsUtilsPyprojectTypeFixCommand" = {
    "command_name": "type-fix",
    "short_name": "f",
    "help": "🛠 <f> Create and run the type-fix workflow from ./.ai/linters issues files.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TEST_RUNTIME_COMMAND: "StackOpsUtilsPyprojectTestRuntimeCommand" = {
    "command_name": "test-runtime",
    "short_name": "R",
    "help": "🧪 <R> Create and run the runtime-test workflow for Python files under the current directory.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_TEST_REFERENCE_COMMAND: "StackOpsUtilsPyprojectTestReferenceCommand" = {
    "command_name": "test-reference",
    "short_name": "r",
    "help": "🔎 <r> Validate _PATH_REFERENCE targets in a repository.",
    "subcommands": {},
}

STACKOPS_UTILS_PYPROJECT_SUBCOMMANDS: "StackOpsUtilsPyprojectSubcommands" = {
    "init-project": STACKOPS_UTILS_PYPROJECT_INIT_PROJECT_COMMAND,
    "upgrade-packages": STACKOPS_UTILS_PYPROJECT_UPGRADE_PACKAGES_COMMAND,
    "type-hint": STACKOPS_UTILS_PYPROJECT_TYPE_HINT_COMMAND,
    "type-check": STACKOPS_UTILS_PYPROJECT_TYPE_CHECK_COMMAND,
    "type-fix": STACKOPS_UTILS_PYPROJECT_TYPE_FIX_COMMAND,
    "test-runtime": STACKOPS_UTILS_PYPROJECT_TEST_RUNTIME_COMMAND,
    "test-reference": STACKOPS_UTILS_PYPROJECT_TEST_REFERENCE_COMMAND,
}

STACKOPS_UTILS_PYPROJECT_COMMAND: "StackOpsUtilsPyprojectCommand" = {
    "command_name": "pyproject",
    "short_name": "p",
    "help": "🐍 <p> Pyproject bootstrap and typing utilities",
    "subcommands": STACKOPS_UTILS_PYPROJECT_SUBCOMMANDS,
}

STACKOPS_UTILS_FILE_EDIT_COMMAND: "StackOpsUtilsFileEditCommand" = {
    "command_name": "edit",
    "short_name": "e",
    "help": "✏ <e> Open a file in the default editor.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_DOWNLOAD_COMMAND: "StackOpsUtilsFileDownloadCommand" = {
    "command_name": "download",
    "short_name": "d",
    "help": "↓ <d> Download a file from a URL and optionally decompress it.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_PDF_MERGE_COMMAND: "StackOpsUtilsFilePDFMergeCommand" = {
    "command_name": "pdf-merge",
    "short_name": "p",
    "help": "◫ <p> Merge PDF files into one.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_PDF_COMPRESS_COMMAND: "StackOpsUtilsFilePDFCompressCommand" = {
    "command_name": "pdf-compress",
    "short_name": "c",
    "help": "↧ <c> Compress a PDF file.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_READ_DB_COMMAND: "StackOpsUtilsFileReadDBCommand" = {
    "command_name": "read-db",
    "short_name": "r",
    "help": "🗃 <r> TUI DB Visualizer.",
    "subcommands": {},
}

STACKOPS_UTILS_FILE_SUBCOMMANDS: "StackOpsUtilsFileSubcommands" = {
    "edit": STACKOPS_UTILS_FILE_EDIT_COMMAND,
    "download": STACKOPS_UTILS_FILE_DOWNLOAD_COMMAND,
    "pdf-merge": STACKOPS_UTILS_FILE_PDF_MERGE_COMMAND,
    "pdf-compress": STACKOPS_UTILS_FILE_PDF_COMPRESS_COMMAND,
    "read-db": STACKOPS_UTILS_FILE_READ_DB_COMMAND,
}

STACKOPS_UTILS_FILE_COMMAND: "StackOpsUtilsFileCommand" = {
    "command_name": "file",
    "short_name": "f",
    "help": "📁 <f> File, document, and database utilities",
    "subcommands": STACKOPS_UTILS_FILE_SUBCOMMANDS,
}

STACKOPS_UTILS_SUBCOMMANDS: "StackOpsUtilsSubcommands" = {
    "machine": STACKOPS_UTILS_MACHINE_COMMAND,
    "pyproject": STACKOPS_UTILS_PYPROJECT_COMMAND,
    "file": STACKOPS_UTILS_FILE_COMMAND,
}

STACKOPS_UTILS_COMMAND: "StackOpsUtilsCommand" = {
    "command_name": "utils",
    "short_name": "u",
    "help": "<u> Utility commands",
    "subcommands": STACKOPS_UTILS_SUBCOMMANDS,
}

STACKOPS_SEEK_SEEK_COMMAND: "StackOpsSeekSeekCommand" = {
    "command_name": "seek",
    "short_name": None,
    "help": "stackops search helper",
    "subcommands": {},
}

STACKOPS_SEEK_SUBCOMMANDS: "StackOpsSeekSubcommands" = {"seek": STACKOPS_SEEK_SEEK_COMMAND}

STACKOPS_SEEK_COMMAND: "StackOpsSeekCommand" = {
    "command_name": "seek",
    "short_name": "s",
    "help": "<s> Search across files, text matches, and code symbols",
    "subcommands": STACKOPS_SEEK_SUBCOMMANDS,
}

STACKOPS_FIRE_COMMAND: "StackOpsFireCommand" = {"command_name": "fire", "short_name": "f", "help": "<f> Fire and manage jobs", "subcommands": {}}

STACKOPS_PREVIEW_COMMAND: "StackOpsPreviewCommand" = {
    "command_name": "preview",
    "short_name": "p",
    "help": "<p> Preview files and launch reader backends",
    "subcommands": {},
}

STACKOPS_SUBCOMMANDS: "StackOpsSubcommands" = {
    "devops": STACKOPS_DEVOPS_COMMAND,
    "cloud": STACKOPS_CLOUD_COMMAND,
    "terminal": STACKOPS_TERMINAL_COMMAND,
    "agents": STACKOPS_AGENTS_COMMAND,
    "utils": STACKOPS_UTILS_COMMAND,
    "seek": STACKOPS_SEEK_COMMAND,
    "fire": STACKOPS_FIRE_COMMAND,
    "preview": STACKOPS_PREVIEW_COMMAND,
}

STACKOPS_COMMAND: "StackOpsCommandHierarchy" = {
    "command_name": "stackops",
    "short_name": None,
    "help": "StackOps CLI - Manage your machine configurations and workflows",
    "subcommands": STACKOPS_SUBCOMMANDS,
}

STACKOPS_CLI_HIERARCHY: "StackOpsCommandHierarchy" = STACKOPS_COMMAND

# q = STACKOPS_CLI_HIERARCHY["subcommands"]["preview"]
# w = StackOpsTerminalKillCommand[""]
# q = STACKOPS_PREVIEW_COMMAND["subcommands"]
