// The purpose-built views of the Vault page, in the shape features.js describes. `load` paths are relative to this folder.
// One view can stand behind several commands. `aimed` tells the view which of them was opened: `path` is the command and `focus` the part of the
// view it is about.
const aimed = (file, path, focus) => () => import(`../spaces/vault/${file}.js`).then((view) => ({ createPart: view.createPart, open: (context, given) => view.open(context, { ...given, path, focus }) }));
const filePage = (path, focus) => ({ path, space: "vault", part: "file", load: aimed("file_page", path, focus) });
const bitwardenPage = (path, focus) => ({ path, space: "vault", part: "bitwarden", load: aimed("bitwarden_page", path, focus) });

export const VAULT_FEATURES = [
  filePage("devops vault validate", "check"),
  filePage("devops vault stats", "holds"),
  filePage("devops vault init", "create"),
  { path: "devops vault subset", load: () => import("../spaces/vault/copy_sheet.js") },
  bitwardenPage("devops vault bitwarden login-and-unlock", "unlock"),
  bitwardenPage("devops vault bitwarden search", "find"),
  bitwardenPage("devops vault bitwarden sync", "sync"),
  bitwardenPage("devops vault bitwarden clean-cache", "cache"),
];
