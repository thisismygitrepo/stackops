// The purpose-built views of the Settings page, in the shape features.js describes. `load` paths are relative to this folder.
// Several commands share one view. Each hands that view one more word with whatever it was opened with, saying which command led there:
// `action` for the commands that work on a settings file, `step` for the steps of the guided setup. The view uses it to land on the right
// card with the keyboard on the right button.
const shared = (load, word) => async () => {
  const view = await load();
  return { createPart: view.createPart, open: (context, given) => view.open(context, { ...given, ...word }) };
};
const files = (action) => shared(() => import("../spaces/settings/files.js"), { action });
const step = (id) => shared(() => import("../spaces/settings/setup.js"), { step: id });

export const SETTINGS_FEATURES = [
  { path: "devops config path", space: "settings", part: "files", load: files("path") },
  { path: "devops config init", space: "settings", part: "files", load: files("init") },
  { path: "devops config validate", space: "settings", part: "files", load: files("validate") },
  { path: "devops config edit", space: "settings", part: "files", load: files("edit") },
  { path: "devops config export-example", space: "settings", part: "files", load: files("export-example") },
  { path: "devops config setup email", space: "settings", part: "setup", load: step("email") },
  { path: "devops config setup agent", space: "settings", part: "setup", load: step("agent") },
  { path: "devops config setup data", space: "settings", part: "setup", load: step("data") },
  { path: "devops config setup dotfiles", space: "settings", part: "setup", load: step("dotfiles") },
  { path: "devops config setup layouts", space: "settings", part: "setup", load: step("layouts") },
  { path: "devops config setup secrets", space: "settings", part: "setup", load: step("secrets") },
  { path: "devops config init-script", space: "settings", part: "scripts", load: () => import("../spaces/settings/scripts.js") },
  { path: "devops config copy-assets", space: "settings", part: "assets", load: () => import("../spaces/settings/assets.js") },
  { path: "devops config interactive", load: () => import("../spaces/settings/wizard.js") },
];
