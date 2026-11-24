import { openFind } from "./find_sheet.js";

// Tools that have a view built for them in place of the form made from their options, by command path. Wherever such a tool is opened (a card,
// search, the toolbox, another view), its feature opens. A feature's module is fetched the first time it is needed, so the app's start does not
// grow with them, and one that fails to load takes only itself down.
// A feature's module exports `open(context, { preset })`: `context` is what a page gets ({ activity, tools, openReport, openSearch }) and `preset`
// holds values by the command's parameter names, from whoever opened it. A feature that is a page of its own also exports `createPart(context)`,
// which returns `{ element, show(rest) }`; the page it belongs to shows it at `#/<space>/<part>`, and its `open` goes to that address.
// `tools.open(path, { plain: true })` still opens the tool's own form, for a feature that offers every option of the command.
const FEATURES = [
  { path: "devops config setup multiplexer", space: "sessions", part: "multiplexer", load: () => import("./spaces/sessions/multiplexer.js") },
  { path: "devops config terminal config-shell", space: "sessions", part: "shell-profile", load: () => import("./spaces/sessions/shell_profile.js") },
  { path: "devops config terminal starship-theme", space: "sessions", part: "starship", load: () => import("./spaces/sessions/starship_theme.js") },
  { path: "devops config terminal wezterm-theme", space: "sessions", part: "wezterm", load: () => import("./spaces/sessions/wezterm_theme.js") },
  { path: "devops config terminal ghostty-theme", space: "sessions", part: "ghostty", load: () => import("./spaces/sessions/ghostty_theme.js") },
  { path: "utils machine kill-process", space: "machine", part: "processes", load: () => import("./spaces/machine/processes.js") },
  { path: "utils machine list-devices", space: "machine", part: "devices", load: () => import("./spaces/machine/devices.js") },
  { path: "utils machine mount", space: "machine", part: "mount", load: () => import("./spaces/machine/mount.js") },
  { path: "utils machine window", space: "machine", part: "windows", load: () => import("./spaces/machine/windows.js") },
  { path: "devops self update", space: "machine", part: "update", load: () => import("./spaces/machine/update.js") },
];

export function createGuides(context) {
  const guides = { seek: () => openFind({ activity: context.activity }) };
  for (const feature of FEATURES) guides[feature.path] = async (given) => (await feature.load()).open(context, given);
  return guides;
}

// The pages of their own that belong to one space, by the word in their address.
export const partLoaders = (space) => Object.fromEntries(FEATURES.filter((feature) => feature.space === space).map((feature) => [feature.part, feature.load]));
