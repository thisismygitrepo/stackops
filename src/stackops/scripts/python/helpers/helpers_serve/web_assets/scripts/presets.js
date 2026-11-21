export const DASHBOARDS = [
  {
    id: "status", icon: "📊", title: "Machine status", file: "devops_status.html",
    blurb: "System, shell, repositories, SSH, managed configs, apps, and backups.",
    arguments: ["devops", "self", "status", "--as-html"],
    actions: [
      { label: "Update StackOps", path: "devops self update" },
      { label: "Sync dotfiles", path: "devops config dotfiles sync" },
      { label: "Install software", path: "devops software install" },
    ],
  },
  {
    id: "doctor", icon: "🩺", title: "Agents doctor", file: "agents_doctor.html",
    blurb: "Agent binaries, configuration, hooks, plugins, skills, and instruction provenance.",
    arguments: ["agents", "doctor", "--as-html"],
    actions: [
      { label: "Add a skill", path: "agents add-skill" },
      { label: "Add an MCP server", path: "agents add-mcp" },
    ],
  },
  {
    id: "reset", icon: "🧼", title: "Agents reset preview", file: "agents_reset_preview.html",
    blurb: "What a reset of agent customizations and .ai folders would remove. Read-only.",
    arguments: ["agents", "reset", "--as-html"],
    actions: [{ label: "Open the reset command", path: "agents reset" }],
  },
  {
    id: "environment", icon: "🌍", title: "Environment", file: "environment_variables.html",
    blurb: "Environment variables, with secret-looking values left out.",
    arguments: ["utils", "machine", "environment", "ENV", "--as-html"],
    actions: [],
  },
  {
    id: "path", icon: "🧭", title: "PATH", file: "environment_path.html",
    blurb: "PATH entries in lookup order.",
    arguments: ["utils", "machine", "environment", "PATH", "--as-html"],
    actions: [],
  },
];

export const QUICK_ACTIONS = [
  { label: "Machine specs", path: "utils machine specs", run: true },
  { label: "Network addresses", path: "devops network show-address", run: true },
  { label: "Session summary", path: "terminal summary", run: true },
  { label: "Agents status", path: "agents status", run: true },
  { label: "Repositories", path: "devops repos list", run: true },
  { label: "Dotfiles status", path: "devops config dotfiles status", run: true },
  { label: "Startup programs", path: "utils machine autostart", run: true },
  { label: "Browse software", path: "devops software explore", run: true },
  { label: "Install software", path: "devops software install", run: false },
  { label: "Update StackOps", path: "devops self update", run: false },
  { label: "Sync dotfiles", path: "devops config dotfiles sync", run: false },
  { label: "Sync repositories", path: "devops repos sync", run: false },
];

export const SERIES = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"],
};

export const TERMINAL_THEME = {
  background: "#00000000", foreground: "#e6e5e0", cursor: "#6da7ec", cursorAccent: "#161615", selectionBackground: "rgba(109, 167, 236, 0.32)",
  black: "#262624", red: "#e66767", green: "#35b85a", yellow: "#d9a21a", blue: "#5598e7", magenta: "#d55181", cyan: "#2bb8a6", white: "#c3c2b7",
  brightBlack: "#75736d", brightRed: "#f08a8a", brightGreen: "#5fd27e", brightYellow: "#f2c14e", brightBlue: "#86b6ef", brightMagenta: "#e79ac0",
  brightCyan: "#5fd4c4", brightWhite: "#f0efec",
};
