// The purpose-built views of the Dotfiles page, in the shape features.js describes. `load` paths are relative to this folder.
export const DOTFILES_FEATURES = [
  { path: "devops config dotfiles export", space: "dotfiles", part: "export", load: () => import("../spaces/dotfiles/export.js") },
  { path: "devops config dotfiles import", space: "dotfiles", part: "import", load: () => import("../spaces/dotfiles/import.js") },
  { path: "devops config dotfiles register", load: () => import("../spaces/dotfiles/register.js") },
];
