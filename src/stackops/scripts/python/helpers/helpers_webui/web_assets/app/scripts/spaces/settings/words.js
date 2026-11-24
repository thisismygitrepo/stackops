export const API = "/api/settings";
export const HASH = "#/settings";
export const FILES_HASH = "#/settings/files";
export const SETUP_HASH = "#/settings/setup";
export const SCRIPTS_HASH = "#/settings/scripts";
export const ASSETS_HASH = "#/settings/assets";
export const WIZARD_PATH = "devops config interactive";
export const WIZARD_TITLE = "Set up this machine";

// The settings files the CLI manages, in its order: what each is called here, what it is for, and the page that works with it.
export const FILES = {
  config: { emoji: "⚙️", title: "StackOps defaults", about: "The cloud, coding agent, multiplexers and email that commands use when you name none.", used: { label: "Setup", href: SETUP_HASH } },
  layouts: { emoji: "🧩", title: "Terminal layouts", about: "Workspaces of tabs and panes that start in one click.", used: { label: "Sessions", href: "#/sessions" } },
  dotfiles: { emoji: "📂", title: "Dotfiles list", about: "Which settings files are kept in your dotfiles folder, and where each one belongs.", used: { label: "Dotfiles", href: "#/dotfiles" } },
  data: { emoji: "💾", title: "Backup list", about: "The files and folders that are backed up to your cloud storage.", used: { label: "Data", href: "#/data" } },
  secrets: { emoji: "🔐", title: "Vault", about: "Your saved logins and keys.", used: { label: "Vault", href: "#/vault" } },
  repos: { emoji: "🌿", title: "Projects list", about: "The repositories StackOps clones and keeps up to date.", used: { label: "Projects", href: "#/projects" } },
  software: { emoji: "📦", title: "Your own apps", about: "Apps you added to the install catalog.", used: { label: "Apps", href: "#/apps" } },
  prompts: { emoji: "💬", title: "Saved prompts", about: "Named prompts this project shares with everyone who works in it.", used: { label: "Agents", href: "#/agents" } },
  mcp: { emoji: "🔌", title: "MCP servers", about: "Tool servers this project offers to coding agents.", used: { label: "Agents", href: "#/agents" } },
};

// The commands that share the Settings files view, by the word the feature list hands over, with the button each one puts the keyboard on.
export const FILE_ACTIONS = { path: "", init: "create", validate: "check", edit: "edit", "export-example": "example" };
export const FILE_TOOLS = [
  ["devops config edit", "Edit a file", "Choose the editor the file opens in."],
  ["devops config validate", "Check a file", "The check as the command prints it."],
  ["devops config init", "Create a file", "What Create it does on a card, as a run to watch."],
  ["devops config path", "Where a file lives", "The paths as the command prints them."],
  ["devops config export-example", "Export an example", "Only the file, only the schema, or over your real file."],
];

export const SCHEMA_WORDS = {
  current: "Beside the file and up to date",
  outdated: "Beside the file, but older than the one StackOps ships",
  missing: "Not beside the file",
};

// What the page says about one file. `check` is the answer to its check once that is in: `ok` is true, false, or null when the check itself could not run.
export function standingOf(file, check) {
  if (!file.available) return { id: "unavailable", label: "No project here", tone: "" };
  if (file.blocked) return { id: "blocked", label: "Not a file", tone: "bad" };
  if (!file.exists) return { id: "missing", label: "Not created yet", tone: "" };
  if (!check) return { id: "checking", label: "Checking…", tone: "" };
  if (check.ok === true) return { id: "valid", label: "Passes its check", tone: "good" };
  if (check.ok === false) return { id: "problem", label: "Has a problem", tone: "bad" };
  return { id: "unchecked", label: "Could not be checked", tone: "warn" };
}

export const needsAttention = (standing) => ["problem", "blocked", "unchecked"].includes(standing.id);

// The CLI's message names the file by its whole path, which the card already shows.
export const tidyProblem = (problem, path) => problem.replaceAll(path, "this file").replace(/^Invalid \w+ file this file( at)?:?\s*/i, (_, at) => (at ? "At " : "")).trim();

// The guided setup, in the CLI's order. `path` is the command behind a step.
export const STEPS = [
  { id: "cloud", path: "devops config setup cloud", emoji: "⛅", title: "Cloud for backups" },
  { id: "email", path: "devops config setup email", emoji: "📧", title: "Email notifications" },
  { id: "agent", path: "devops config setup agent", emoji: "🤖", title: "Default coding agent" },
  { id: "multiplexer", path: "devops config setup multiplexer", emoji: "🪟", title: "Default multiplexer" },
  { id: "data", path: "devops config setup data", emoji: "💾", title: "Backup list" },
  { id: "dotfiles", path: "devops config setup dotfiles", emoji: "📄", title: "Dotfiles list" },
  { id: "layouts", path: "devops config setup layouts", emoji: "🧩", title: "Starter layouts" },
  { id: "secrets", path: "devops config setup secrets", emoji: "🔐", title: "Vault" },
];

// Whether each step is done, from the server's reading. A step whose state cannot be read (the settings file fails its check) is neither.
export function stepsDone(setup) {
  const chosen = (set) => (setup.settings_problem ? null : set);
  const filled = (list) => (list.problem ? null : (list.count ?? 0) > 0);
  return {
    cloud: chosen(setup.cloud !== ""),
    email: chosen(setup.email_profile !== "" && setup.email_address !== ""),
    agent: chosen(setup.agent !== ""),
    multiplexer: chosen(setup.session_multiplexer !== "" && setup.agent_multiplexer !== ""),
    data: filled(setup.backups),
    dotfiles: filled(setup.dotfiles),
    layouts: filled(setup.layouts),
    secrets: filled(setup.logins),
  };
}

export const SCRIPTS = [
  {
    id: "init", emoji: "🐚", title: "Shell start-up", runnable: false,
    about: "What a terminal loads each time it opens, once your shell profile points to it. It puts StackOps on the program search path and defines its short commands.",
  },
  {
    id: "ia", emoji: "🧭", title: "Machine setup", runnable: true,
    about: "For a machine that has nothing yet. It makes the StackOps commands available in one terminal session, taken from the released version, and then starts the setup wizard.",
  },
  {
    id: "live", emoji: "🛰️", title: "Machine setup from GitHub", runnable: true,
    about: "The same as Machine setup, but the commands come from the newest code on GitHub and not from a release.",
  },
];

export const ASSET_SETS = {
  scripts: { emoji: "📜", title: "Scripts", which: "scripts", about: "The helper every StackOps short command goes through, for your shell and for Nushell." },
  settings: { emoji: "🎛️", title: "Settings", which: "settings", about: "Ready-made settings for the tools StackOps works with: terminals, editors, file managers, prompts." },
};
