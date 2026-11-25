// The purpose-built views of the settings tools (`devops config`), in the shape features.js describes. They are views of Home, where the
// settings overview sits. `load` paths are relative to this folder.
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
  { path: "devops config path", space: "home", part: "files", load: files("path") },
  { path: "devops config init", space: "home", part: "files", load: files("init") },
  { path: "devops config validate", space: "home", part: "files", load: files("validate") },
  { path: "devops config edit", space: "home", part: "files", load: files("edit") },
  { path: "devops config export-example", space: "home", part: "files", load: files("export-example") },
  { path: "devops config setup email", space: "home", part: "setup", load: step("email") },
  { path: "devops config setup agent", space: "home", part: "setup", load: step("agent") },
  { path: "devops config setup data", space: "home", part: "setup", load: step("data") },
  { path: "devops config setup dotfiles", space: "home", part: "setup", load: step("dotfiles") },
  { path: "devops config setup layouts", space: "home", part: "setup", load: step("layouts") },
  { path: "devops config setup secrets", space: "home", part: "setup", load: step("secrets") },
  { path: "devops config init-script", space: "home", part: "scripts", load: () => import("../spaces/settings/scripts.js") },
  { path: "devops config copy-assets", space: "home", part: "assets", load: () => import("../spaces/settings/assets.js") },
  { path: "devops config interactive", load: () => import("../spaces/settings/wizard.js") },
];
