export const VIEW_KEY = "stackops-serve-view";

export const SPACES = [
  { id: "home", hash: "#/", label: "Home", glyph: "home", title: "Home" },
  { id: "apps", hash: "#/apps", label: "Apps", glyph: "apps", title: "Apps" },
  { id: "projects", hash: "#/projects", label: "Projects", glyph: "branch", title: "Projects" },
  { id: "sessions", hash: "#/sessions", label: "Sessions", glyph: "layers", title: "Sessions" },
  { id: "agents", hash: "#/agents", label: "Agents", glyph: "bot", title: "Agents" },
  { id: "dotfiles", hash: "#/dotfiles", label: "Dotfiles", glyph: "sync", title: "Dotfiles" },
  { id: "data", hash: "#/data", label: "Data", glyph: "database", title: "Data" },
  { id: "network", hash: "#/network", label: "Network", glyph: "globe", title: "Network" },
  { id: "machine", hash: "#/machine", label: "Machine", glyph: "cpu", title: "Machine" },
  { id: "reports", hash: "#/reports", label: "Reports", glyph: "chart", title: "Reports" },
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
  utils: "Utilities", "utils machine": "Machine", "utils file": "Files", "utils pyproject": "Python projects", fire: "Launch", seek: "Find anything",
  "devops software install": "Install apps", "devops self update": "Update StackOps", "devops self status": "Machine status",
  "devops network show-address": "Network addresses", "devops network share-server": "Share a folder", "devops network share-terminal": "Share this terminal",
  "utils machine clean-drive": "Free up disk space", "utils machine kill-process": "Stop a process", "utils machine autostart": "Startup programs",
  "utils machine specs": "Machine specs", "agents run-prompt": "Run a prompt", "agents run-interactive": "Start a chat", "agents add-skill": "Add a skill",
  "agents add-mcp": "Add an MCP server", "agents doctor": "Agent health check", "terminal run": "Launch a layout", "terminal summary": "Running sessions", "terminal list": "Saved layouts",
  "devops network send": "Send files", "devops network receive": "Receive files", "devops network share-temp-file": "Share a temporary link",
  "devops network vscode-share": "Share this workspace", "devops network ssh": "SSH", "devops network ssh install-server": "Set up SSH access",
  "devops network ssh add-key": "Add an SSH key", "devops network ssh debug": "Diagnose SSH", "devops network ssh map-port": "Forward a port",
  "devops network ssh change-port": "Change the SSH port", "devops network device connect-wifi": "Connect to Wi-Fi", "devops network cloudflare": "Cloudflare",
  "devops network cloudflare run-tunnel": "Run a tunnel", "devops network cloudflare connect-warp": "Connect WARP", "utils machine window": "Manage windows",
  "utils machine mount": "Mount a device", "utils machine list-devices": "Storage devices", "utils machine environment": "Environment",
  "devops repos sync": "Sync projects", "devops repos register": "Register projects", "devops repos action": "Act on every project",
  "devops config dotfiles": "Dotfiles", "devops config dotfiles sync": "Sync dotfiles", "devops config dotfiles collect": "Collect my settings",
  "devops config dotfiles export": "Export dotfiles", "devops config dotfiles import": "Import dotfiles", "devops config dotfiles register": "Add a dotfile",
  "devops data sync": "Back up or retrieve", "devops data register": "Add a backup", "devops data list": "What is backed up",
  "devops data encrypt": "Encrypt a file or folder", "devops data decrypt": "Decrypt a file", "devops data subset": "Split off part of the list",
  "devops data validate": "Check the backup list", cloud: "Cloud storage", "cloud sync": "Keep a folder in sync", "cloud copy": "Upload or download",
  "cloud mount": "Mount cloud storage", "cloud transfer": "Move files between machines",
  "devops config terminal": "Terminal look", "devops config setup": "Guided setup", "terminal kill": "End a session", "terminal attach": "Open a session",
  "agents browser": "Browser automation", "agents browser launch": "Open a browser", "agents browser batch-launch": "Open saved profiles",
  "agents browser close": "Close a browser", "agents browser batch-close": "Close saved profiles", "agents browser status": "Open browsers",
  "agents browser declutter": "Slim down a profile", "agents browser replicate": "Copy a profile", "agents browser install": "Set up browser tools",
  "agents computer": "Desktop control", "agents computer control": "Turn on desktop control", "agents computer status": "Desktop control status",
  "agents local": "Local models", "agents local doctor": "Model server check", "agents local discover": "Find a model", "agents local install": "Install vLLM",
  "agents local serve": "Start a model server", "agents second-brain": "Second Brain", "agents second-brain init": "Set up Second Brain",
  "agents second-brain status": "Second Brain activity", "agents second-brain prune": "Clean up Second Brain", "agents parallel": "Parallel runs",
  "agents parallel create": "Split a job", "agents parallel create-context": "Gather a to-do list", "agents parallel run": "Run a saved workflow",
  "agents parallel collect": "Collect the results", "agents parallel create-template": "Starter files", "agents iter": "Loops",
  "agents iter status": "Loops in progress", "agents iter close": "Close finished tabs", "agents iter clean": "Clear old loop records",
  "agents config": "Agent lists", "agents config path": "Where a list lives", "agents config init": "Create a list", "agents config validate": "Check a list",
  "agents init": "Set up a project", "agents reset": "Reset agents", "agents ask": "Ask a question",
};

// Options that only make sense on a command line: output formats, alternate renderers, and file overrides the app already picks for you.
export const HIDDEN_FLAGS = new Set(["--json", "--as-html", "--tui", "--plain", "--custom-path", "--specs-path", "--show-format", "--non-interactive", "--reference"]);

// Read-only tools: safe to run on arrival so the page shows something before anyone presses a button.
export const LIVE_NAMES = new Set([
  "list", "status", "path", "summary", "specs", "stats", "history", "show-address", "list-devices", "autostart", "accounts", "tunnel-status", "validate",
  "doctor", "report", "discover",
]);

export const ESSENTIAL_FLAGS = {
  "devops software install": ["--update"],
  "agents run-prompt": ["--agent", "--reasoning"],
  "agents run-interactive": ["--agent"],
  "terminal run": ["--choose-layouts", "--backend", "--on-conflict"],
  "devops config dotfiles sync": ["--method", "--on-conflict"],
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
  "agents browser declutter": ["--browser", "--profile", "--all"],
  "agents browser replicate": ["--browser", "--profile", "--target", "--native"],
  "agents browser install": ["--tool", "--agent"],
  "agents computer control": ["--headless"],
  "agents local doctor": ["--backend", "--host"],
  "agents local discover": ["--backend", "--capability", "--sort"],
  "agents local serve": ["--port"],
  "agents second-brain init": ["--overwrite"],
  "agents second-brain prune": ["--apply"],
  "agents parallel create": ["--agent", "--prompt", "--context-path", "--job-name", "--run"],
  "agents parallel run": ["--agent", "--source"],
  "agents parallel create-context": ["--agent"],
  "agents iter status": ["--all"],
  "agents iter close": ["--all", "--dry-run", "--retain-previous"],
  "agents iter clean": ["--all", "--dry-run"],
  "agents config path": ["--source"],
  "agents config init": ["--source"],
  "agents config validate": ["--source"],
  "agents init": ["--root", "--include-scripts", "--add-gitignore"],
  "agents reset": ["--scope", "--resource", "--apply"],
  "agents ask": ["--agent", "--second-brain", "--reasoning"],
};

export const REPORTS = [
  { id: "status", glyph: "cpu", title: "Machine status", file: "devops_status.html", blurb: "System, shell, repositories, SSH, managed settings, apps, and backups.", arguments: ["devops", "self", "status", "--as-html"] },
  { id: "doctor", glyph: "bot", title: "Agents health", file: "agents_doctor.html", blurb: "Agent programs, configuration, hooks, plugins, skills, and where instructions come from.", arguments: ["agents", "doctor", "--as-html"] },
  { id: "reset", glyph: "trash", title: "Agent cleanup preview", file: "agents_reset_preview.html", blurb: "What a reset of agent customizations would remove. Nothing is changed.", arguments: ["agents", "reset", "--as-html"] },
  { id: "environment", glyph: "globe", title: "Environment", file: "environment_variables.html", blurb: "Environment variables, with secret-looking values left out.", arguments: ["utils", "machine", "environment", "ENV", "--as-html"] },
  { id: "path", glyph: "arrow", title: "Program search path", file: "environment_path.html", blurb: "Where this machine looks for programs, in lookup order.", arguments: ["utils", "machine", "environment", "PATH", "--as-html"] },
];

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
