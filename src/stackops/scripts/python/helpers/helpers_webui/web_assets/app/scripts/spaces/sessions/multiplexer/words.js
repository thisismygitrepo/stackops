export const PATH = "devops config setup multiplexer";
export const ADDRESS = "#/sessions/multiplexer";
export const API = "/api/terminal/multiplexer";
export const ROLE_IDS = ["session", "agent"];
export const LEDE = "A multiplexer keeps terminal sessions running in the background, so they outlive the window they started in. StackOps uses the ones chosen here whenever a task does not name another.";

// What each one is, in a sentence. The server says which ones exist and how each stands on this machine; one it names that is not here is shown by its own name.
const KNOWN = {
  tmux: { title: "tmux", about: "The long-standing standard, found on almost every server. Sessions hold windows, and windows hold panes." },
  zellij: { title: "Zellij", about: "A newer workspace of tabs and panes that shows its shortcuts on screen." },
  tuios: { title: "TUIOS", about: "A window manager inside the terminal, with tiling windows and workspaces. It can tell which windows hold coding agents." },
  herdr: { title: "Herdr", about: "Made for running coding agents side by side. Workspaces hold tabs and panes, and it keeps track of each agent's status." },
  aoe: { title: "AoE", about: "Agent of Empires, a session manager for coding agents. Each agent gets a session of its own, and sessions can be grouped." },
};
export const wordsOf = (name) => KNOWN[name] ?? { title: name, about: "" };

// What else follows the defaults, beyond starting, listing, opening and ending sessions, which every multiplexer can do. A card says after
// each `what` whether it works with that multiplexer.
export const CAPABILITIES = {
  batch: { label: "Batch runs", what: "A batch run goes through every tab of a layouts file, a few at a time." },
  save: { label: "Save as layout", what: "A running session can be saved as a layout." },
  browsers: { label: "Agent browsers", what: "Browsers opened for agents run inside a session." },
  mounts: { label: "Cloud mounts", what: "Mounted cloud storage is kept running inside a session." },
  agents: { label: "Agents list", what: "The Agents page lists the agents that are running." },
};

export const ROLES = {
  session: {
    label: "Sessions", pick: "Use for sessions", holds: "Runs your sessions", stalled: "sessions cannot start",
    uses: "Layouts start in it. The Sessions page lists what runs there, and opens, ends and saves it.",
    saved: (title) => `Sessions now start in ${title}.`,
  },
  agent: {
    label: "Agents", pick: "Use for agents", holds: "Lists your agents", stalled: "the Agents page has nothing to list",
    uses: "The Agents page looks in it for the agents that are running.",
    saved: (title) => `The Agents page now looks in ${title}.`,
  },
};

// How one multiplexer stands on this machine, and the way forward where it cannot be picked. `platform` is the system's name as the app shows it.
export function standingOf(item, platform) {
  const { title } = wordsOf(item.name);
  const apps = item.in_catalog ? `#/apps/${encodeURIComponent(item.name)}` : "";
  if (!item.supported) return { id: "unsupported", pill: [`Not for ${platform}`, ""], reason: `${title} does not run on ${platform}.`, href: "", action: "" };
  if (!item.installed) {
    const reason = apps ? "It is not on this machine yet. Install it and it can be picked here." : `It is not on this machine, and the app catalog has no way to install it on ${platform}.`;
    return { id: "missing", pill: ["Not installed", ""], reason, href: apps, action: "Install from Apps" };
  }
  // The CLI's own sentence, without the marks it puts around a program's name.
  if (item.problem) return { id: "problem", pill: ["Needs attention", "warn"], reason: item.problem.replaceAll("`", ""), href: apps, action: "Update in Apps" };
  return { id: "ready", pill: ["Installed", "good"], reason: "", href: "", action: "" };
}

export const isReady = (item) => item.supported && item.installed && !item.problem;
