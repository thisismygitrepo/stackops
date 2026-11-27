export const VIEW_KEY = "stackops-webui-view";

export const SPACES = [
  { id: "home", hash: "#/", label: "Home", glyph: "home", title: "Home" },
  { id: "apps", hash: "#/apps", label: "Apps", glyph: "apps", title: "Apps" },
  { id: "projects", hash: "#/projects", label: "Projects", glyph: "branch", title: "Projects" },
  { id: "sessions", hash: "#/sessions", label: "Sessions", glyph: "layers", title: "Sessions" },
  { id: "scripts", hash: "#/scripts", label: "Scripts", glyph: "terminal", title: "Scripts" },
  { id: "agents", hash: "#/agents", label: "Agents", glyph: "bot", title: "Agents" },
  { id: "dotfiles", hash: "#/dotfiles", label: "Dotfiles", glyph: "sync", title: "Dotfiles" },
  { id: "data", hash: "#/data", label: "Data", glyph: "database", title: "Data" },
  { id: "network", hash: "#/network", label: "Network", glyph: "globe", title: "Network" },
  { id: "machine", hash: "#/machine", label: "Machine", glyph: "cpu", title: "Machine" },
  { id: "security", hash: "#/security", label: "Security", glyph: "shield", title: "Security" },
  { id: "vault", hash: "#/vault", label: "Vault", glyph: "key", title: "Vault" },
  { id: "tools", hash: "#/tools", label: "Toolbox", glyph: "cube", title: "Toolbox" },
];

export const WORDS = {
  devops: "DevOps", ssh: "SSH", onedrive: "OneDrive", mcp: "MCP", pdf: "PDF", ocr: "OCR", db: "database", wsl: "WSL", vscode: "VS Code", cli: "CLI",
  api: "API", ip: "IP", wifi: "Wi-Fi", tui: "TUI", pwsh: "PowerShell", warp: "WARP", url: "URL", json: "JSON", os: "OS", id: "ID", html: "HTML",
  gpg: "GPG", pyproject: "Python project", directory: "folder", utils: "utilities", attrs: "details", deps: "dependencies", repos: "repositories", config: "settings",
  env: "environment", cpu: "CPU", pid: "process ID", nw: "network", t3: "T3", uv: "uv", wezterm: "WezTerm", ghostty: "Ghostty", tmux: "tmux",
};

export const TOOL_TITLES = {
  devops: "DevOps", "devops self": "StackOps itself", "devops software": "Software", "devops config": "Settings", "devops repos": "Repositories",
  "devops data": "Backups", "devops vault": "Vault", "devops network": "Network", "devops security": "Security", "devops scripts": "Scripts",
  utils: "Utilities", "utils machine": "Machine", "utils file": "Files", "utils pyproject": "Python projects", fire: "Launch", seek: "Find in files",
  "devops software install": "Install apps", "devops software uninstall": "Delete apps", "devops self update": "Update StackOps", "devops self status": "Machine status",
  "devops network show-address": "Network addresses", "devops network share-server": "Share a folder", "devops network share-terminal": "Share this terminal",
  "utils machine clean-drive": "Free up disk space", "utils machine kill-process": "Processes", "utils machine autostart": "Startup programs",
  "utils machine autostart-add": "Add a startup script", "utils machine autostart-remove": "Remove a startup script",
  "utils machine specs": "Machine specs", "agents run-prompt": "Run a prompt", "agents run-interactive": "Start a chat", "agents add-skill": "Add a skill",
  "agents add-mcp": "Add an MCP server", "agents doctor": "Agent health check", "terminal run": "Launch a layout", "terminal summary": "Running sessions", "terminal list": "Saved layouts",
  "devops network send": "Send files", "devops network receive": "Receive files", "devops network share-temp-file": "Share a temporary link",
  "devops network vscode-share": "Share this workspace", "devops network ssh": "SSH", "devops network ssh install-server": "Set up SSH access",
  "devops network ssh add-key": "Add an SSH key", "devops network ssh debug": "Diagnose SSH", "devops network ssh map-port": "Forward a port",
  "devops network ssh change-port": "Change the SSH port", "devops network device connect-wifi": "Connect to Wi-Fi", "devops network cloudflare": "Cloudflare",
  "devops network cloudflare run-tunnel": "Run a tunnel", "devops network cloudflare connect-warp": "Connect WARP", "devops network cloudflare tunnel-status": "Cloudflare tunnel status", "utils machine window": "Manage windows",
  "utils machine mount": "Mount a device", "utils machine list-devices": "Storage devices", "utils machine environment": "Environment",
  "devops repos sync": "Sync projects", "devops repos register": "Register projects", "devops repos action": "Pull, commit or push a folder",
  "devops config dotfiles": "Dotfiles", "devops config dotfiles sync": "Sync dotfiles", "devops config dotfiles collect": "Collect my settings",
  "devops config dotfiles export": "Move to a new machine", "devops config dotfiles import": "Bring settings from another machine", "devops config dotfiles register": "Add one file",
  "devops data sync": "Back up or retrieve", "devops data register": "Add a backup", "devops data list": "What is backed up",
  "devops data encrypt": "Encrypt a file or folder", "devops data decrypt": "Decrypt a file", "devops data subset": "Split off part of the list",
  "devops data validate": "Check the backup list", cloud: "Cloud storage", "cloud sync": "Keep a folder in sync", "cloud copy": "Upload or download",
  "cloud mount": "Mount cloud storage", "cloud transfer": "Move files between machines",
  "devops config terminal": "Terminal look", "devops config setup": "Guided setup", "terminal kill": "End a session", "terminal attach": "Open a session", "terminal export": "Save sessions as layouts", "devops config terminal config-shell": "Shell profile",
  "devops config setup multiplexer": "Default multiplexer", "devops config terminal starship-theme": "Starship prompt",
  "devops config path": "Where a settings file lives", "devops config init": "Create a settings file", "devops config validate": "Check a settings file",
  "devops config edit": "Edit a settings file", "devops config export-example": "Example of a settings file", "devops config init-script": "Setup scripts",
  "devops config interactive": "Set up this machine", "devops config copy-assets": "Packaged files",
  "devops config setup email": "Email notifications", "devops config setup agent": "Default coding agent", "devops config setup data": "Add a backup, step by step",
  "devops config setup dotfiles": "Add a dotfile, step by step", "devops config setup layouts": "Starter layouts", "devops config setup secrets": "Create the vault",
  "agents browser": "Browser automation", "agents browser launch": "Open a browser", "agents browser batch-launch": "Open saved profiles",
  "agents browser close": "Close a browser", "agents browser batch-close": "Close saved profiles", "agents browser status": "Open browsers",
  "agents browser declutter": "Slim down a profile", "agents browser replicate": "Copy a profile", "agents browser install": "Set up browser tools",
  "agents browser profiles": "Profiles and sign-ins",
  "agents computer": "Desktop control", "agents computer control": "Turn on desktop control", "agents computer status": "Desktop control status",
  "agents local": "Local models", "agents local doctor": "Model server check", "agents local discover": "Find a model", "agents local install": "Install vLLM",
  "agents local serve": "Start a model server", "agents second-brain": "Second Brain", "agents second-brain init": "Set up Second Brain",
  "agents second-brain status": "Second Brain activity", "agents second-brain prune": "Clean up Second Brain", "agents iter": "Loops",
  "agents iter status": "Loops in progress", "agents iter close": "Close finished tabs", "agents iter clean": "Clear old loop records",
  "agents config": "Agent lists", "agents config path": "Where a list lives", "agents config init": "Create a list", "agents config validate": "Check a list",
  "agents init": "Set up a project", "agents reset": "Reset agents", "agents ask": "Ask a question",
  "devops security scan": "Scan apps or a file", "devops security status": "Security overview", "devops security list": "Installed apps",
  "devops security history": "Scan history", "devops security report": "Look at one scan", "devops security export": "Export a scan",
  "devops security install": "Install from a scan", "devops security upload": "Upload a file to cloud storage", "devops security download": "Download from Google Drive",
  "devops vault stats": "What the vault holds", "devops vault validate": "Check the vault file", "devops vault add": "Add a secret", "devops vault rotate": "Replace a secret", "devops vault delete": "Remove a secret",
  "devops vault subset": "Copy part of the vault", "devops vault init": "Create a vault file", "devops vault path": "Where the vault is kept", "devops vault search": "Search the vault",
  "devops vault load": "Load secrets into a terminal", "devops vault bitwarden": "Bitwarden", "devops vault bitwarden search": "Find a Bitwarden login",
  "devops vault bitwarden load": "Load a Bitwarden item into a terminal",
  "devops vault bitwarden login-and-unlock": "Unlock Bitwarden", "devops vault bitwarden sync": "Sync Bitwarden", "devops vault bitwarden clean-cache": "Clear the Bitwarden cache",
  "devops vault bitwarden export-session": "Hand the Bitwarden session to a terminal",
  "devops scripts run": "Run a script or a command", "devops scripts list": "Saved scripts", "devops scripts path": "Where scripts are kept", "devops scripts edit": "Edit a script",
};

// What a tool's card and search entry say about it, for the tools whose view does more than their command's one-line help says (features.js).
export const TOOL_BLURBS = {
  "devops config setup multiplexer": "Choose where sessions start and where agents are looked for: tmux, Zellij, TUIOS, Herdr or AoE.",
  "devops config terminal config-shell": "See which shells load StackOps' setup, and set one up.",
  "devops config terminal starship-theme": "See which prompt look is in use and choose another, in a terminal or by name.",
  "devops config terminal wezterm-theme": "See which theme WezTerm uses, and choose another in a terminal or by name.",
  "devops config terminal ghostty-theme": "See which theme Ghostty uses and change it, in its own picker or by name.",
  "devops config dotfiles export": "Pack the whole dotfiles folder into one protected archive to carry, share or send.",
  "devops config dotfiles import": "See what an archive from the other machine would change here, then put it in place.",
  "devops config dotfiles register": "Keep one more settings file in your dotfiles folder and on your list.",
  "devops config path": "See where each StackOps settings file is and whether it is there.",
  "devops config init": "Create a missing settings file from the example StackOps ships.",
  "devops config validate": "See which settings files pass their check, and what is wrong with one that does not.",
  "devops config edit": "Open a settings file in an editor. It is checked when you close it.",
  "devops config export-example": "Read the example StackOps ships for a settings file and save a copy.",
  "devops config init-script": "Read what the shell start-up and machine setup scripts would do before anything runs.",
  "devops config interactive": "One guided run for a new machine. You tick what to install and set up.",
  "devops config copy-assets": "Compare the scripts and settings StackOps ships with the copies on this machine, then copy them.",
  "devops config setup email": "Choose the mail account and address for notifications.",
  "devops config setup agent": "Choose the coding agent that commands start when you name none.",
  "devops config setup data": "Add a file or folder to your backup list by answering a few questions.",
  "devops config setup dotfiles": "Add a settings file to your dotfiles list by answering a few questions.",
  "devops config setup layouts": "Put the starter terminal layouts into your layouts file.",
  "devops config setup secrets": "Create your vault file with a first login.",
  "devops vault validate": "Shows whether each vault file is usable, and what is wrong if not.",
  "devops vault stats": "Counts of logins, secrets and values, and what is due.",
  "devops vault subset": "Tick the logins to copy and write them to another vault file.",
  "devops vault init": "Start a vault file for yourself or for this project.",
  "devops vault bitwarden login-and-unlock": "Sign in with the API key in your vault and open Bitwarden.",
  "devops vault bitwarden search": "Search your Bitwarden logins and copy a password or code.",
  "devops vault bitwarden sync": "Bring this machine's copy of your Bitwarden vault up to date.",
  "devops vault bitwarden clean-cache": "Remove the session and search results saved on this machine.",
  "devops network ssh install-server": "See whether this machine accepts SSH connections, and switch it on.",
  "devops network ssh add-key": "Choose whose keys may sign in to this machine over SSH.",
  "devops network ssh map-port": "Reach a port on another machine as if it were on this one.",
  "devops network device connect-wifi": "The network this machine is on, and the ones it can join.",
  "devops network cloudflare connect-warp": "Send traffic through Cloudflare and watch your address change.",
  "devops network cloudflare tunnel-status": "Which tunnels exist, where each is connected, and what it publishes.",
  "devops network cloudflare run-tunnel": "Pick a tunnel and run it on this machine.",
  "devops security install": "Choose a saved scan, see which of its apps are clean and have a copy to download, and install the ones you tick.",
  "devops security export": "Save one scan as four files in a new folder. Their sizes are shown before anything is written.",
  "devops security upload": "Send one file to your cloud storage and get a link to share.",
  "devops security download": "Paste a link, see what the file is, and fetch it.",
  "devops data encrypt": "Lock a file or a folder with a password or one of your GPG keys.",
  "devops data decrypt": "Open a locked file, after seeing how it was locked and what will come out.",
  "utils machine kill-process": "See what is running and what uses the most CPU and memory, and stop what you do not need.",
  "utils machine autostart": "See what starts with this computer and at sign-in, what is running now, and turn off what you do not need.",
  "utils machine autostart-add": "Pick one of your scripts and have it start every time you sign in.",
  "utils machine autostart-remove": "Stop a script you added from starting when you sign in. The script itself is kept.",
  "utils machine list-devices": "Every disk and volume on this computer, how full each one is, and a way to mount, unmount or eject it.",
  "utils machine mount": "Pick a disk, say where it should appear, and mount it.",
  "utils machine window": "See every open window by app and screen. Bring one to the front, minimize it or close it.",
  "devops self update": "See what is installed, what is newer, and update in one click.",
  "utils machine environment": "The variables a task starts with, and the folders this machine searches for programs, in lookup order.",
};

// Options that only make sense on a command line: output formats, alternate renderers, and file overrides the app already picks for you.
export const HIDDEN_FLAGS = new Set(["--json", "--as-html", "--tui", "--plain", "--custom-path", "--specs-path", "--show-format", "--non-interactive", "--reference", "--save"]);

// Read-only tools: safe to run on arrival, and again on every change in their form, so the sheet shows something before anyone presses a button.
// Design choice: every one is listed by its full path, not matched by a name such as "status" or "report". A new command stays behind its Start button
// until someone has run it and added it here. Never add one that changes anything, or whose output holds secrets (`devops vault search`).
export const LIVE_PATHS = new Set([
  "devops software check", "devops software list", "devops software report", "devops software path", "devops software validate", "devops data list", "devops data path",
  "devops data validate", "devops repos path", "devops repos validate", "devops repos list", "devops repos version list", "devops repos version status", "devops config dotfiles path",
  "devops config dotfiles validate", "devops config dotfiles status", "devops config path", "devops config validate", "devops config terminal tmux-style status", "devops vault stats",
  "devops vault path", "devops vault validate", "devops scripts list", "devops scripts path", "devops security status", "devops security list", "devops security report",
  "devops security history", "devops network ssh debug", "devops network cloudflare tunnel-status", "devops network show-address", "devops self status", "devops self explore-cli search",
  "devops self explore-python-api search", "cloud onedrive status", "cloud onedrive accounts", "cloud onedrive list", "cloud onedrive config-path", "terminal list", "terminal path",
  "terminal validate", "terminal summary", "agents browser status", "agents browser profiles", "agents computer status", "agents iter status", "agents second-brain status",
  "agents local doctor", "agents local discover", "agents config path", "agents config validate", "agents doctor", "agents status", "utils machine specs", "utils machine list-devices",
  "utils machine autostart",
]);

// What a read-only tool starts with when the CLI insists on a choice without marking it as required. Keyed by parameter name; a switch is "on".
export const ARRIVAL_VALUES = {
  "terminal validate": { source: "user" },
  "devops vault validate": { source: "user" },
  "agents iter status": { all_workspaces: "on" },
};

// Tools that hand whatever follows their own arguments on to a script or program. The command tree does not carry this, so the list is kept by hand.
export const PASSTHROUGH_TOOLS = new Set(["devops scripts run", "fire run", "utils file ocr", "utils file scrape", "agents local serve"]);

// Options a read-only tool's sheet leaves out, by parameter name. The sheet re-runs on every change, so nothing in it may act: on `agents status`, Btw makes real agent calls,
// Output and Force write files, and Format clashes with the `--json` the sheet asks for. The Agents page offers Btw as a button behind a confirmation.
// The scan tools' Format and View only shape the table that `--json` replaces. The last three are switches that ask for a picker in a terminal, which a sheet does not have.
export const OMITTED_FIELDS = {
  "agents status": ["output_format", "output", "force", "btw"], "devops security history": ["format_type"], "devops security report": ["format_type", "view"],
  "devops scripts path": ["interactive"], "agents iter status": ["interactive"], "terminal summary": ["choose_session"],
};

// Path fields whose suggestions start in the home folder, by parameter name. What they ask for is a place on this machine, not a file of the working folder.
export const HOME_PATH_FIELDS = { "devops repos register": ["directory"] };

export const ESSENTIAL_FLAGS = {
  "devops software install": ["--update"],
  "agents run-prompt": ["--agent", "--reasoning", "--interactive"],
  "agents add-skill": ["--scope"],
  "agents add-mcp": ["--agent", "--scope"],
  "agents run-interactive": ["--agent", "--followup", "--fork"],
  "terminal run": ["--choose-layouts", "--backend", "--on-conflict"],
  "terminal export": ["--sessions", "--all", "--output", "--merge", "--command-source"],
  "devops config dotfiles sync": ["--which", "--method", "--on-conflict"],
  "devops repos action": ["--pull", "--push", "--commit", "--message", "--status"],
  "utils machine clean-drive": ["--dry-run", "--max-risk", "--category"],
  "devops network share-server": ["--port", "--over-internet"],
  "devops self update": ["--sync-configs"],
  "devops data sync": ["--which", "--cloud", "--source"],
  "devops data register": ["--group", "--name", "--encryption", "--note"],
  "agents browser launch": ["--browser", "--profile", "--new-window"],
  "agents browser batch-launch": ["--browser", "--max-profiles"],
  "agents browser close": ["--browser", "--port", "--profile"],
  "agents browser batch-close": ["--browser"],
  "agents browser status": ["--all", "--browser"],
  "agents browser profiles": ["--browser", "--native"],
  "agents browser declutter": ["--browser", "--profile", "--all"],
  "agents browser replicate": ["--browser", "--profile", "--target", "--native"],
  "agents browser install": ["--tool", "--agent"],
  "agents computer control": ["--headless"],
  "agents local doctor": ["--backend", "--host"],
  "agents local discover": ["--backend", "--capability", "--sort"],
  "agents local serve": ["--port"],
  "agents second-brain init": ["--overwrite"],
  "agents second-brain prune": ["--apply"],
  "agents iter status": ["--all"],
  "cloud onedrive list": ["--account"],
  "agents iter close": ["--all", "--dry-run", "--retain-previous"],
  "agents iter clean": ["--all", "--dry-run"],
  "agents config path": ["--source"],
  "agents config init": ["--source"],
  "agents config validate": ["--source"],
  "agents init": ["--root", "--include-scripts", "--add-gitignore"],
  "agents reset": ["--scope", "--resource", "--apply"],
  "agents ask": ["--agent", "--second-brain", "--reasoning"],
  "devops security scan": ["--path", "--all", "--upload"],
  "devops security report": ["--run"],
  "devops security install": ["--all", "--run"],
  "devops security export": ["--output", "--run"],
};

// Runs a page only starts behind its own confirmation: the words the command begins with, then any switch it must also carry, wherever that sits.
// Activity offers no "Run again" for these, because that would repeat them without asking. Left out on purpose, as repeating them is harmless:
// collecting dotfiles (refuses once done), saving a session over a layout (only shown when it failed), installing from a link (same source again).
export const CONFIRMED_RUNS = [
  "utils machine clean-drive", "terminal kill", "devops data sync down", "agents status --btw", "devops repos action --push", "devops security scan",
  "devops config terminal config-shell", "devops config copy-assets", "devops self update --dev", "devops self update --sync-configs",
  "devops config init-script --run", "devops config setup layouts --overwrite", "devops config export-example --overwrite",
];

// Runs that are a chat with a coding agent, written the way the entries above are. One changes files while it runs and ends only when the person
// leaves it, so the refresh that follows a finished run never comes: the pages read again when the Activity panel is put away over one.
export const CHAT_RUNS = ["agents run-interactive", "agents run-prompt --interactive"];

// Names for the installer's bundles (`devops software install <name> --group`), whose own names are abbreviations.
export const BUNDLE_TITLES = {
  sysabc: "System basics", shell: "Shell upgrades", search: "Search & archive tools", "sys-monitor": "System monitors", "code-analysis": "Code analysis & Git",
  termabc: "Terminal essentials", dev: "Developer workstation", "dev-utils": "Developer utilities", eye: "Terminal eye candy", agents: "AI agents",
  terminal: "Terminal emulators", browsers: "Browsers", editors: "Code editors", "db-all": "All database tools", "db-cli": "Database command-line tools",
  "db-desktop": "Database desktop apps", "db-web": "Database web apps", "db-tui": "Database terminal apps", media: "Media", gui: "Desktop apps",
  nw: "Networking", "file-sharing": "File sharing", productivity: "Productivity",
};

export const QUICK_TASKS = [
  { title: "Install apps", blurb: "Search the catalog and install in one go.", glyph: "download", tint: 252, hash: "#/apps" },
  { title: "Update StackOps", blurb: "Get the latest version and assets.", glyph: "bolt", tint: 200, tool: "devops self update" },
  { title: "Sync dotfiles", blurb: "Apply or save your managed settings.", glyph: "sync", tint: 165, hash: "#/dotfiles" },
  { title: "Launch a layout", blurb: "Start a saved terminal workspace.", glyph: "layers", tint: 290, hash: "#/sessions" },
  { title: "Share a folder", blurb: "Serve files to another device.", glyph: "share", tint: 30, tool: "devops network share-server" },
  { title: "Run a prompt", blurb: "Hand a task to a coding agent.", glyph: "sparkle", tint: 330, tool: "agents run-prompt" },
  { title: "Free up disk space", blurb: "See what takes up room and choose what to remove.", glyph: "trash", tint: 10, hash: "#/machine/cleanup" },
  { title: "Sync repositories", blurb: "Clone and update every project.", glyph: "branch", tint: 140, tool: "devops repos sync" },
];
